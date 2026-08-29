"""The Stock sheet round-trip module (CONTEXT.md: Stock sheet, Source cells).

The organizer's master CSV is both the catalog input and the completed report
shape. This module owns the whole round-trip rule: loading and validating the
file, preserving each row's source cells verbatim, and building the report
rows. It is the one home for that rule (architecture umbrella U1).

The session facade calls `load_catalog` at setup and `build_report_rows` at
export; the SQLite adapter persists the preserved source cells through the
module's contract. The domain `Item` carries only domain facts — file-format
preservation lives here, keyed by Item ID.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from .domain import CatalogError, Item, SourceCells, money

STOCK_SHEET_HEADER = [
    "ItemID",
    "ItemName",
    "Price",
    "Inventory",
    "Sales",
    "Revenue",
]

_HEADER_LOWER = [cell.lower() for cell in STOCK_SHEET_HEADER]


@dataclass(frozen=True)
class LoadedCatalog:
    """The outcome of loading a Stock sheet: domain items plus source cells."""

    items: list[Item]
    source_cells: dict[str, SourceCells]


def load_catalog(path: str | Path) -> LoadedCatalog:
    """Validate a Stock sheet CSV and return its items and preserved source cells.

    Rejects a missing/wrong header, an empty or item-less file, a missing or
    duplicate Item ID, a missing or blank ItemName, a non-numeric Price, and an
    invalid Inventory. Pre-filled Sales/Revenue values are ignored.
    """
    try:
        with open(path, newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle)
            rows = list(reader)
    except OSError as exc:
        raise CatalogError(f"Could not read the Stock sheet CSV: {exc}") from exc

    if not rows:
        raise CatalogError("Stock sheet CSV is empty")

    header = [cell.strip().lower() for cell in rows[0]]
    if header != _HEADER_LOWER:
        raise CatalogError(
            "Stock sheet CSV must have a header row of "
            "ItemID, ItemName, Price, Inventory, Sales, Revenue"
        )

    items: list[Item] = []
    source_cells: dict[str, SourceCells] = {}
    seen_ids: set[str] = set()
    for row in rows[1:]:
        cells = [cell.strip() for cell in row]
        if not any(cells):
            continue
        item_id = cells[0]
        if not item_id:
            raise CatalogError(f"Row is missing an Item ID: {cells!r}")
        if item_id in seen_ids:
            raise CatalogError(f"Duplicate Item ID: {item_id!r}")
        seen_ids.add(item_id)

        name = cells[1] if len(cells) > 1 else ""
        if not name:
            raise CatalogError(f"Row is missing an ItemName: {cells!r}")

        if len(cells) < 3 or not cells[2]:
            raise CatalogError(f"Row is missing a price: {cells!r}")
        try:
            price = money(cells[2])
        except CatalogError:
            raise CatalogError(
                f"Price for item {item_id!r} is not a number: {cells[2]!r}"
            ) from None

        inventory_text = cells[3] if len(cells) > 3 else ""
        quantity: int | None = None
        if inventory_text:
            try:
                quantity = int(inventory_text)
            except ValueError as exc:
                raise CatalogError(
                    f"Starting quantity for {item_id!r} is not a whole number: "
                    f"{inventory_text!r}"
                ) from exc
            if quantity < 0:
                raise CatalogError(
                    f"Starting quantity for {item_id!r} cannot be negative"
                )

        source_cells[item_id] = (
            row[0],
            row[1] if len(row) > 1 else "",
            row[2] if len(row) > 2 else "",
            row[3] if len(row) > 3 else "",
        )
        items.append(
            Item(
                item_id=item_id,
                name=name,
                price=price,
                starting_quantity=quantity,
            )
        )

    if not items:
        raise CatalogError("Stock sheet CSV contains no items")

    return LoadedCatalog(items=items, source_cells=source_cells)


def build_report_rows(
    catalog_items: list[Item],
    sold_by_item: dict[str, tuple[int, Decimal]],
    source_cells: dict[str, SourceCells],
) -> list[list[str]]:
    """Build the six-column report rows in catalog order.

    Each row passes its source cells through verbatim when available, falling
    back to cells synthesized from the domain `Item` otherwise, then appends
    the computed `Sales` and `Revenue`.
    """
    rows: list[list[str]] = []
    for item in catalog_items:
        cells = source_cells.get(item.item_id)
        if cells is not None:
            passthrough = list(cells)
        else:
            inventory = (
                str(item.starting_quantity)
                if item.starting_quantity is not None
                else ""
            )
            passthrough = [item.item_id, item.name, str(item.price), inventory]
        units, revenue = sold_by_item.get(item.item_id, (0, Decimal("0")))
        rows.append(passthrough + [str(units), str(revenue)])
    return rows