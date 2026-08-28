"""End-of-event reporting module (spec #29).

The single home of the reconciliation rule (CONTEXT.md: End-of-day, Items
sold): final-state aggregation of units and recorded revenue, the end-of-day
figures, and the three CSV exports. Pure — no persistence bookkeeping, no UI
knowledge — so it is testable without a store and the session facade keeps its
single responsibility.

The Stock sheet report rows delegate to the Stock sheet module's
`build_report_rows`; no six-column logic is duplicated here.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from . import stock_sheet
from .domain import (
    CASH,
    COMPLETED,
    OCTOPUS,
    VOUCHER,
    CashAdjustment,
    Item,
    Money,
    PosError,
    Sale,
)

SALES_HEADER = [
    "device", "sale_seq", "created_at", "updated_at", "status",
    "total", "cash", "octopus", "voucher",
]
ITEMS_HEADER = ["device", "sale_seq", "status", "item", "quantity", "price"]


@dataclass
class ItemSoldRow:
    """One item's sold count, presentation-ready (CONTEXT.md: Items sold).

    `item_name` is resolved from the catalog so the screen renders rows
    directly; `item_id` keeps the trace back to the master file.
    """

    item_id: str
    item_name: str
    count: int


@dataclass
class EndOfDay:
    """Per-device end-of-day reconciliation figures (CONTEXT.md: End-of-day).

    `sold_rows` is the ordered, presentation-ready `ItemSoldRow` list — the one
    representation of items sold, replacing the old `sold_counts` dict. Rows
    follow catalog order; a sold item absent from the catalog is appended with
    its item ID as the display name so no sold item is dropped.
    """

    expected_cash: Money
    octopus_total: Money
    voucher_total: Money
    sold_rows: list[ItemSoldRow]
    voids: list[Sale]
    cash_adjustments: list[CashAdjustment]


def aggregate_sold_and_revenue(sales: list[Sale]) -> dict[str, tuple[int, Money]]:
    """Final-state, non-void units and recorded revenue per Item ID.

    The single source of truth for "sold". Corrections appear in their final
    state (one record per sale); voided sales are excluded. Revenue is the
    actually-recorded settled value.
    """
    sold: dict[str, tuple[int, Money]] = {}
    for sale in sales:
        if sale.status != COMPLETED:
            continue
        for line in sale.line_items:
            units, revenue = sold.get(line.item_id, (0, Decimal("0")))
            sold[line.item_id] = (units + line.quantity, revenue + line.total)
    return sold


def voids(sales: list[Sale]) -> list[Sale]:
    """The voided (non-completed) sales in the given list."""
    return [s for s in sales if s.status != COMPLETED]


def build_end_of_day(
    float_amount: Money,
    sales: list[Sale],
    adjustments: list[CashAdjustment],
    catalog: list[Item],
) -> EndOfDay:
    """Build the reconciliation figures for one device.

    Expected cash is the float plus cash sales plus cash adjustments. Octopus
    and voucher totals cover only completed, final-state sales. Sold rows are
    the non-void per-item counts in catalog order with catalog names; a sold
    item absent from the catalog is appended with its item ID as the display
    name, so the figures never drop an item the aggregation reports.
    """
    completed = [s for s in sales if s.status == COMPLETED]
    cash = sum((s.tender_sum(CASH) for s in completed), Decimal("0"))
    octopus = sum((s.tender_sum(OCTOPUS) for s in completed), Decimal("0"))
    voucher = sum((s.tender_sum(VOUCHER) for s in completed), Decimal("0"))
    sold_by_item = aggregate_sold_and_revenue(sales)
    sold_rows = [
        ItemSoldRow(item_id=item.item_id, item_name=item.name, count=units)
        for item in catalog
        if (units := sold_by_item.get(item.item_id, (0, Decimal("0")))[0]) > 0
    ]
    catalog_ids = {item.item_id for item in catalog}
    for item_id, (units, _revenue) in sold_by_item.items():
        # Fallback for a sold item absent from the catalog (only reachable if
        # the catalog changes mid-event): keep the row, keyed by its item ID.
        if units and item_id not in catalog_ids:
            sold_rows.append(
                ItemSoldRow(item_id=item_id, item_name=item_id, count=units)
            )
    adjustment_sum = sum((a.amount for a in adjustments), Decimal("0"))
    return EndOfDay(
        expected_cash=float_amount + cash + adjustment_sum,
        octopus_total=octopus,
        voucher_total=voucher,
        sold_rows=sold_rows,
        voids=voids(sales),
        cash_adjustments=adjustments,
    )


# -- CSV row builders -------------------------------------------------------


def sales_rows(sales: list[Sale]) -> list[list[str]]:
    """One row per sale, including voided sales with their `voided` status."""
    rows: list[list[str]] = [list(SALES_HEADER)]
    for sale in sales:
        rows.append(
            [
                sale.device_name,
                str(sale.seq),
                sale.created_at.isoformat(),
                sale.updated_at.isoformat(),
                sale.status,
                str(sale.total),
                str(sale.tender_sum(CASH)),
                str(sale.tender_sum(OCTOPUS)),
                str(sale.tender_sum(VOUCHER)),
            ]
        )
    return rows


def item_rows(sales: list[Sale]) -> list[list[str]]:
    """One row per line item."""
    rows: list[list[str]] = [list(ITEMS_HEADER)]
    for sale in sales:
        for line in sale.line_items:
            rows.append(
                [
                    sale.device_name,
                    str(sale.seq),
                    sale.status,
                    line.item_name,
                    str(line.quantity),
                    str(line.price),
                ]
            )
    return rows


def stock_sheet_rows(
    catalog: list[Item],
    sold_by_item: dict[str, tuple[int, Money]],
    source_cells: dict[str, stock_sheet.SourceCells],
) -> list[list[str]]:
    """The six-column Stock sheet report rows, header first.

    Delegates to the Stock sheet module's report-row builder; the six-column
    shape and source-cell passthrough live there (ADR-0003).
    """
    return [list(stock_sheet.STOCK_SHEET_HEADER)] + stock_sheet.build_report_rows(
        catalog, sold_by_item, source_cells
    )


# -- export coordinator -----------------------------------------------------


def write_export(
    directory: str | Path,
    sales: list[Sale],
    catalog: list[Item],
    source_cells: dict[str, stock_sheet.SourceCells],
    device_name: str,
) -> list[Path]:
    """Write the three export files atomically and return their paths.

    Every row is precomputed first; the files are written as temp files and
    renamed into place. The destination is either the old export or the new
    one, never a half-written mix: a failure during precompute or temp-writing
    leaves the destination untouched; a rename-phase failure (vanishingly
    rare) raises an error naming the files.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    sold_by_item = aggregate_sold_and_revenue(sales)
    targets = [
        directory / "sales.csv",
        directory / "items.csv",
        directory / f"stocks-{device_name}.csv",
    ]
    rows = [
        sales_rows(sales),
        item_rows(sales),
        stock_sheet_rows(catalog, sold_by_item, source_cells),
    ]
    temps = [target.with_name(target.name + ".tmp") for target in targets]
    try:
        for temp, file_rows in zip(temps, rows):
            with open(temp, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerows(file_rows)
    except OSError:
        for temp in temps:
            try:
                os.remove(temp)
            except OSError:
                pass
        raise
    try:
        for temp, target in zip(temps, targets):
            os.replace(temp, target)
    except OSError:
        raise PosError(
            "Export failed while renaming files into place: "
            + ", ".join(str(target) for target in targets)
        ) from None
    return targets