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
import tempfile
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import NoReturn

from . import stock_sheet
from .domain import (
    CASH,
    COMPLETED,
    OCTOPUS,
    STOCK_REPORT_FILE_PREFIX,
    STOCK_REPORT_FILE_SUFFIX,
    VOUCHER,
    CashAdjustment,
    ExportError,
    Item,
    Money,
    Sale,
    SetupError,
    SourceCells,
    validate_device_name,
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
    source_cells: dict[str, SourceCells],
) -> list[list[str]]:
    """The six-column Stock sheet report rows, header first.

    Delegates to the Stock sheet module's report-row builder; the six-column
    shape and source-cell passthrough live there (ADR-0003).
    """
    return [list(stock_sheet.STOCK_SHEET_HEADER)] + stock_sheet.build_report_rows(
        catalog, sold_by_item, source_cells
    )


# -- export coordinator -----------------------------------------------------


def _cleanup_temps(temps: list[Path]) -> None:
    """Remove any temp files still present after a failed export step."""
    for temp in temps:
        try:
            os.remove(temp)
        except OSError:
            pass


def _abort_export(
    phase: str, temps: list[Path], targets: list[Path], cause: OSError
) -> NoReturn:
    """Clean up temps and surface a failed export step as an `ExportError`."""
    _cleanup_temps(temps)
    raise ExportError(
        f"Export failed while {phase}: " + ", ".join(str(t) for t in targets)
    ) from cause


def write_export(
    directory: str | Path,
    sales: list[Sale],
    catalog: list[Item],
    source_cells: dict[str, SourceCells],
    device_name: str,
) -> list[Path]:
    """Write the three export files atomically and return their paths.

    Every row is precomputed first; the files are written as short, unique
    temp files in the destination folder and renamed into place one at a
    time, so each destination is either the old file or the new one, never a
    truncated mix. Any failure removes every temp file and surfaces as an
    `ExportError`; a failure before the renames leaves existing destinations
    untouched, while a mid-rename failure can leave a mix of old and new
    files (per-file atomicity only, ADR-0003).
    """
    try:
        device_name = validate_device_name(device_name)
    except SetupError as exc:
        raise ExportError(str(exc)) from None
    directory = Path(directory)
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ExportError(
            f"Export failed: cannot create the export folder {directory}"
        ) from exc
    targets = [
        directory / "sales.csv",
        directory / "items.csv",
        directory
        / f"{STOCK_REPORT_FILE_PREFIX}{device_name}{STOCK_REPORT_FILE_SUFFIX}",
    ]
    temps: list[Path] = []
    try:
        sold_by_item = aggregate_sold_and_revenue(sales)
        rows = [
            sales_rows(sales),
            item_rows(sales),
            stock_sheet_rows(catalog, sold_by_item, source_cells),
        ]
    except OSError as exc:
        _abort_export("building the rows", temps, targets, exc)
    try:
        for target, file_rows in zip(targets, rows):
            fd, temp_name = tempfile.mkstemp(
                prefix="pos-export-", suffix=".tmp", dir=directory
            )
            temps.append(Path(temp_name))
            handle = None
            try:
                handle = os.fdopen(fd, "w", newline="", encoding="utf-8")
            finally:
                if handle is None:
                    try:
                        os.close(fd)
                    except OSError:
                        pass
            with handle:
                writer = csv.writer(handle)
                writer.writerows(file_rows)
    except OSError as exc:
        _abort_export("writing the files", temps, targets, exc)
    try:
        for temp, target in zip(temps, targets):
            os.replace(temp, target)
    except OSError as exc:
        _abort_export("renaming files into place", temps, targets, exc)
    return targets
