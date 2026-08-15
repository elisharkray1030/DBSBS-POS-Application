"""05 — Manual sold-out marking.

Sold-out is a per-device manual flag. The item dims in the list and cannot be
added to a new sale; it never affects the other device.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from pos.domain import CASH, ItemSoldOut, PosError, Tender
from pos.facade import PosSession
from pos.persistence import InMemoryPersistence


def test_cashier_can_mark_an_item_sold_out(configured_session):
    configured_session.mark_sold_out("Mug")
    assert configured_session.is_sold_out("Mug") is True
    stock = {i.name: i for i in configured_session.list_items()}["Mug"]
    assert stock.sold_out is True


def test_sold_out_item_cannot_be_added_to_a_new_sale(configured_session):
    configured_session.mark_sold_out("Mug")
    with pytest.raises(ItemSoldOut):
        configured_session.add_item_to_sale("Mug", 1)


def test_sold_out_is_per_device(clock, catalog_file):
    store_a = InMemoryPersistence()
    store_b = InMemoryPersistence()
    a = PosSession(store_a, clock=clock)
    b = PosSession(store_b, clock=clock)
    for s in (a, b):
        s.set_device_name("Till A")
        s.set_float(500)
        s.load_catalog(catalog_file)
    a.mark_sold_out("Mug")
    assert b.is_sold_out("Mug") is False
    assert b.list_items()[0].sold_out is False


def test_unmark_restores_the_item(configured_session):
    configured_session.mark_sold_out("Mug")
    configured_session.unmark_sold_out("Mug")
    assert configured_session.is_sold_out("Mug") is False
    configured_session.add_item_to_sale("Mug", 1)
    configured_session.settle_current_sale([Tender(CASH, Decimal("60"), tendered=Decimal("60"))])
    assert configured_session.get_sale(1).total == Decimal("60")


def test_sold_out_does_not_affect_existing_sale_line(configured_session):
    configured_session.add_item_to_sale("Mug", 1)
    configured_session.mark_sold_out("Mug")
    configured_session.settle_current_sale([Tender(CASH, Decimal("60"), tendered=Decimal("60"))])
    assert configured_session.get_sale(1).total == Decimal("60")


def test_mark_unknown_item_raises(configured_session):
    with pytest.raises(PosError):
        configured_session.mark_sold_out("Ghost")
