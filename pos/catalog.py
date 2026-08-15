"""Catalog loading from the `Name, Price, Quantity` CSV (CONTEXT.md: Catalog).

Delimiter handling beyond comma is parked TBC in docs/open-questions.md, so
comma is the accepted format. An empty quantity column means the item has no
starting quantity (sell-by-demand).
"""

from __future__ import annotations

import csv
from pathlib import Path

from .domain import CatalogError, Item, money


def load_catalog(path: str | Path) -> list[Item]:
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        rows = list(reader)

    if not rows:
        raise CatalogError("Catalog CSV is empty")

    header = [cell.strip().lower() for cell in rows[0]]
    if not any(word in header[0] for word in ("name", "item")):
        raise CatalogError("Catalog CSV must have a header row of Name, Price, Quantity")

    items: list[Item] = []
    for row in rows[1:]:
        cells = [cell.strip() for cell in row]
        if not cells or not cells[0]:
            continue
        if len(cells) < 2 or not cells[1]:
            raise CatalogError(f"Row is missing a price: {cells!r}")
        name = cells[0]
        price = money(cells[1])
        quantity_text = cells[2] if len(cells) > 2 and cells[2] else None
        quantity: int | None = None
        if quantity_text is not None:
            try:
                quantity = int(quantity_text)
            except ValueError as exc:
                raise CatalogError(
                    f"Starting quantity for {name!r} is not a whole number: {quantity_text!r}"
                ) from exc
            if quantity < 0:
                raise CatalogError(f"Starting quantity for {name!r} cannot be negative")
        items.append(Item(name=name, price=price, starting_quantity=quantity))
    return items
