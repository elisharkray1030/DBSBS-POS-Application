"""Catalog loading from the organizer's Stock sheet CSV (CONTEXT.md: Stock
sheet).

The only accepted catalog input has the header
`ItemID, ItemName, Price, Inventory, Sales, Revenue`, matched
case-insensitively. Each item's identity is its Item ID (unique per file,
never assigned in-app); `Inventory` sets the starting quantity, a blank value
meaning sell-by-demand; pre-filled `Sales`/`Revenue` values are ignored. The
old `Name, Price, Quantity` format is rejected.
"""

from __future__ import annotations

import csv
from pathlib import Path

from .domain import CatalogError, Item, money

_STOCK_SHEET_HEADER = [
    "itemid",
    "itemname",
    "price",
    "inventory",
    "sales",
    "revenue",
]


def load_catalog(path: str | Path) -> list[Item]:
    try:
        with open(path, newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle)
            rows = list(reader)
    except OSError as exc:
        raise CatalogError(f"Could not read the Stock sheet CSV: {exc}") from exc

    if not rows:
        raise CatalogError("Stock sheet CSV is empty")

    header = [cell.strip().lower() for cell in rows[0]]
    if header != _STOCK_SHEET_HEADER:
        raise CatalogError(
            "Stock sheet CSV must have a header row of "
            "ItemID, ItemName, Price, Inventory, Sales, Revenue"
        )

    items: list[Item] = []
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

        name = cells[1]
        items.append(Item(item_id=item_id, name=name, price=price, starting_quantity=quantity))
    return items
