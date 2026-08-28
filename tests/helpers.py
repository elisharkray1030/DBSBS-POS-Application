"""Shared test helpers."""

from __future__ import annotations

from pos.domain import LineItem


def line_item(session, name, qty):
    """Build a LineItem at the item's current catalog price."""
    stock = {i.name: i for i in session.list_items()}[name]
    return LineItem(item_id=stock.item_id, item_name=name, quantity=qty, price=stock.price)
