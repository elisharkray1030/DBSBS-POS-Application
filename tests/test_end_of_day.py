"""07 — End-of-day view.

Per-device reconciliation figures: expected cash, Octopus total, voucher
total, per-item sold counts, and the voids list. Everything is per-device.
"""

from __future__ import annotations

from decimal import Decimal

from pos.domain import CASH, OCTOPUS, VOUCHER, Tender


def test_end_of_day_shows_octopus_total(configured_session):
    configured_session.add_item_to_sale("Mug", 1)
    configured_session.settle_current_sale([Tender(OCTOPUS, Decimal("60"))])
    configured_session.add_item_to_sale("Badge", 1)
    configured_session.settle_current_sale([Tender(OCTOPUS, Decimal("15"))])
    end_of_day = configured_session.end_of_day()
    assert end_of_day.octopus_total == Decimal("75")
    assert end_of_day.voucher_total == Decimal("0")


def test_end_of_day_shows_voucher_total(configured_session):
    configured_session.add_item_to_sale("Mug", 1)
    configured_session.settle_current_sale([Tender(VOUCHER, Decimal("60"))])
    configured_session.add_item_to_sale("Mug", 1)
    configured_session.settle_current_sale([Tender(VOUCHER, Decimal("60"))])
    end_of_day = configured_session.end_of_day()
    assert end_of_day.voucher_total == Decimal("120")
    assert end_of_day.octopus_total == Decimal("0")


def test_end_of_day_shows_expected_cash_with_adjustments(configured_session):
    configured_session.add_item_to_sale("Mug", 1)
    configured_session.settle_current_sale([Tender(CASH, Decimal("60"), tendered=Decimal("100"))])
    configured_session.record_cash_adjustment(200, "Topping up change")
    configured_session.record_cash_adjustment(-30, "Removing notes")
    end_of_day = configured_session.end_of_day()
    assert end_of_day.expected_cash == Decimal("500") + Decimal("60") + Decimal("170")


def test_end_of_day_shows_per_item_sold_counts_excluding_voids(configured_session):
    configured_session.add_item_to_sale("Mug", 2)
    configured_session.settle_current_sale([Tender(CASH, Decimal("120"), tendered=Decimal("120"))])
    configured_session.add_item_to_sale("Badge", 1)
    configured_session.settle_current_sale([Tender(CASH, Decimal("15"), tendered=Decimal("15"))])
    configured_session.add_item_to_sale("Badge", 3)
    configured_session.settle_current_sale([Tender(CASH, Decimal("45"), tendered=Decimal("45"))])
    configured_session.void_sale(2)

    end_of_day = configured_session.end_of_day()
    assert end_of_day.sold_counts == {"Mug": 2, "Badge": 3}


def test_end_of_day_shows_the_voids_list(configured_session):
    configured_session.add_item_to_sale("Mug", 1)
    configured_session.settle_current_sale([Tender(CASH, Decimal("60"), tendered=Decimal("60"))])
    configured_session.add_item_to_sale("Badge", 1)
    configured_session.settle_current_sale([Tender(CASH, Decimal("15"), tendered=Decimal("15"))])
    configured_session.void_sale(1)

    end_of_day = configured_session.end_of_day()
    assert [v.seq for v in end_of_day.voids] == [1]
    assert end_of_day.expected_cash == Decimal("500") + Decimal("15")


def test_end_of_day_expected_cash_excludes_voided_cash(configured_session):
    configured_session.add_item_to_sale("Mug", 1)
    configured_session.settle_current_sale([Tender(CASH, Decimal("60"), tendered=Decimal("60"))])
    configured_session.void_sale(1)
    end_of_day = configured_session.end_of_day()
    assert end_of_day.expected_cash == Decimal("500")


def test_end_of_day_is_per_device(clock, catalog_file):
    from pos.facade import PosSession
    from pos.persistence import InMemoryPersistence

    a = PosSession(InMemoryPersistence(), clock=clock)
    b = PosSession(InMemoryPersistence(), clock=clock)
    for s in (a, b):
        s.set_device_name("Till")
        s.set_float(500)
        s.load_catalog(catalog_file)

    a.add_item_to_sale("Mug", 1)
    a.settle_current_sale([Tender(CASH, Decimal("60"), tendered=Decimal("60"))])
    b.add_item_to_sale("Badge", 1)
    b.settle_current_sale([Tender(OCTOPUS, Decimal("15"))])

    assert a.end_of_day().sold_counts == {"Mug": 1}
    assert b.end_of_day().sold_counts == {"Badge": 1}
    assert a.end_of_day().octopus_total == Decimal("0")
    assert b.end_of_day().expected_cash == Decimal("500")
