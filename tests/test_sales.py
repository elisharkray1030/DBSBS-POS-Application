"""02 — Build & settle a cash sale.

The cashier builds a sale from the item list, sees a running total, then
settles it in cash. The app computes change, assigns a sequence number and
timestamp, and writes the completed sale to disk immediately.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from pos.domain import CASH, InvalidSettlement, PosError, Tender


def test_item_list_shows_live_remaining_counts(configured_session):
    configured_session.add_item_to_sale("Mug", 2)
    configured_session.settle_current_sale(
        [Tender(CASH, Decimal("120"), tendered=Decimal("200"))]
    )
    by_name = {i.name: i for i in configured_session.list_items()}
    assert by_name["Mug"].remaining == 18
    assert by_name["Badge"].remaining == 50
    assert by_name["Plush Bear"].remaining is None


def test_add_item_builds_running_total(configured_session):
    configured_session.add_item_to_sale("Mug", 1)
    configured_session.add_item_to_sale("Badge", 2)
    assert configured_session.current_sale_total() == Decimal("90")
    items = configured_session.current_sale_items()
    assert [(i.item_name, i.quantity) for i in items] == [("Mug", 1), ("Badge", 2)]


def test_adding_same_item_twice_accumulates_quantity(configured_session):
    configured_session.add_item_to_sale("Mug", 1)
    configured_session.add_item_to_sale("Mug", 3)
    assert configured_session.current_sale_total() == Decimal("240")


def test_set_quantity_replaces_and_zero_removes(configured_session):
    configured_session.add_item_to_sale("Mug", 1)
    configured_session.set_sale_quantity("Mug", 2)
    assert configured_session.current_sale_total() == Decimal("120")
    configured_session.set_sale_quantity("Mug", 0)
    assert configured_session.current_sale_total() == Decimal("0")


def test_cannot_add_unknown_item(configured_session):
    with pytest.raises(PosError):
        configured_session.add_item_to_sale("Ghost", 1)


def test_settle_cash_sale_computes_change(configured_session, clock):
    configured_session.add_item_to_sale("Mug", 1)
    result = configured_session.settle_current_sale(
        [Tender(CASH, Decimal("60"), tendered=Decimal("100"))]
    )
    assert result.change_due == Decimal("40")
    assert result.total == Decimal("60")
    assert result.seq == 1
    assert result.created_at == clock.now


def test_settle_assigns_incrementing_sequence_and_timestamps(configured_session, clock):
    clock.advance(seconds=30)
    configured_session.add_item_to_sale("Mug", 1)
    first = configured_session.settle_current_sale(
        [Tender(CASH, Decimal("60"), tendered=Decimal("60"))]
    )
    clock.advance(seconds=30)
    configured_session.add_item_to_sale("Badge", 1)
    second = configured_session.settle_current_sale(
        [Tender(CASH, Decimal("15"), tendered=Decimal("20"))]
    )
    assert first.seq == 1
    assert second.seq == 2
    assert second.created_at > first.created_at

    sales = configured_session.list_sales()
    assert [s.seq for s in sales] == [1, 2]
    assert sales[0].created_at == first.created_at


def test_settled_sale_is_recorded_and_clears_the_current_sale(configured_session):
    configured_session.add_item_to_sale("Mug", 1)
    configured_session.settle_current_sale(
        [Tender(CASH, Decimal("60"), tendered=Decimal("60"))]
    )
    assert configured_session.current_sale_total() == Decimal("0")
    sale = configured_session.get_sale(1)
    assert sale.status == "completed"
    assert sale.device_name == "Till A"
    assert sale.line_items[0].item_name == "Mug"
    assert sale.total == Decimal("60")


def test_cannot_settle_an_empty_sale(configured_session):
    with pytest.raises(InvalidSettlement):
        configured_session.settle_current_sale(
            [Tender(CASH, Decimal("0"), tendered=Decimal("0"))]
        )


def test_cannot_settle_before_setup(session, catalog_file):
    session.set_device_name("Till A")
    session.load_catalog(catalog_file)
    session.add_item_to_sale("Mug", 1)
    with pytest.raises(PosError):
        session.settle_current_sale(
            [Tender(CASH, Decimal("60"), tendered=Decimal("60"))]
        )
