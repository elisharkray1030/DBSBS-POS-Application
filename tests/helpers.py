"""Shared test helpers."""

from __future__ import annotations

from decimal import Decimal

from pos.domain import CASH, OCTOPUS, VOUCHER, LineItem, Tender


def line_item(session, name, qty):
    """Build a LineItem at the item's current catalog price."""
    stock = {i.name: i for i in session.list_items()}[name]
    return LineItem(item_id=stock.item_id, item_name=name, quantity=qty, price=stock.price)


def three_way_tenders() -> list[Tender]:
    """Return the shared $40 cash / $20 Octopus / $30 voucher settlement."""
    return [
        Tender(CASH, Decimal("40"), tendered=Decimal("50")),
        Tender(OCTOPUS, Decimal("20")),
        Tender(VOUCHER, Decimal("30")),
    ]
