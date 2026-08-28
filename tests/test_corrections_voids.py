"""04 — Correct & void a sale.

A correction edits a recorded sale in place and replaces the original in the
day's totals, keeping the original sequence number and creation time. A void
removes a sale from the totals but keeps it visible in a separate voids list.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from pos.domain import CASH, PosError, Tender
from tests.helpers import line_item as _line


def settle_cash(configured_session, item, qty, price, tendered):
    configured_session.add_item_to_sale(item, qty)
    configured_session.settle_current_sale(
        [Tender(CASH, price, tendered=tendered)]
    )


def test_corrected_sale_replaces_items_and_settlement_in_place(configured_session, clock):
    settle_cash(configured_session, "MUG", 1, Decimal("60"), Decimal("60"))
    clock.advance(minutes=5)

    configured_session.correct_sale(
        seq=1,
        line_items=[_line(configured_session, "Badge", 2)],
        tenders=[Tender(CASH, Decimal("30"), tendered=Decimal("30"))],
    )
    sale = configured_session.get_sale(1)
    assert sale.line_items[0].item_name == "Badge"
    assert sale.total == Decimal("30")
    assert sale.created_at != sale.updated_at
    assert sale.updated_at == clock.now


def test_correction_keeps_sequence_number_and_creation_time(configured_session, clock):
    settle_cash(configured_session, "MUG", 1, Decimal("60"), Decimal("60"))
    created = configured_session.get_sale(1).created_at
    clock.advance(minutes=10)

    configured_session.correct_sale(
        seq=1,
        line_items=[_line(configured_session, "Mug", 2)],
        tenders=[Tender(CASH, Decimal("120"), tendered=Decimal("120"))],
    )
    sale = configured_session.get_sale(1)
    assert sale.seq == 1
    assert sale.created_at == created
    assert sale.updated_at > created


def test_correction_updates_the_days_totals(configured_session):
    settle_cash(configured_session, "MUG", 1, Decimal("60"), Decimal("60"))
    settle_cash(configured_session, "BDG", 1, Decimal("15"), Decimal("15"))
    assert configured_session.running_summary().takings == Decimal("75")

    configured_session.correct_sale(
        seq=1,
        line_items=[_line(configured_session, "Badge", 3)],
        tenders=[Tender(CASH, Decimal("45"), tendered=Decimal("45"))],
    )
    summary = configured_session.running_summary()
    assert summary.takings == Decimal("60")
    assert summary.sale_count == 2


def test_correction_rejects_wrong_tender_total(configured_session):
    settle_cash(configured_session, "MUG", 1, Decimal("60"), Decimal("60"))
    with pytest.raises(PosError):
        configured_session.correct_sale(
            seq=1,
            line_items=[_line(configured_session, "Mug", 1)],
            tenders=[Tender(CASH, Decimal("10"), tendered=Decimal("10"))],
        )


def test_voided_sale_removed_from_totals_but_kept(configured_session):
    settle_cash(configured_session, "MUG", 1, Decimal("60"), Decimal("60"))
    settle_cash(configured_session, "BDG", 1, Decimal("15"), Decimal("15"))

    configured_session.void_sale(1)

    summary = configured_session.running_summary()
    assert summary.takings == Decimal("15")
    assert summary.sale_count == 1
    voids = configured_session.list_voids()
    assert [v.seq for v in voids] == [1]
    assert voids[0].status == "voided"


def test_void_keeps_original_sequence_number(configured_session):
    settle_cash(configured_session, "MUG", 1, Decimal("60"), Decimal("60"))
    configured_session.void_sale(1)
    assert configured_session.list_voids()[0].seq == 1


def test_new_sale_after_void_gets_next_number(configured_session):
    settle_cash(configured_session, "MUG", 1, Decimal("60"), Decimal("60"))
    configured_session.void_sale(1)
    settle_cash(configured_session, "BDG", 1, Decimal("15"), Decimal("15"))
    assert configured_session.get_sale(2).status == "completed"


def test_cannot_void_twice(configured_session):
    settle_cash(configured_session, "MUG", 1, Decimal("60"), Decimal("60"))
    configured_session.void_sale(1)
    with pytest.raises(PosError):
        configured_session.void_sale(1)


def test_cannot_correct_a_voided_sale(configured_session):
    settle_cash(configured_session, "MUG", 1, Decimal("60"), Decimal("60"))
    configured_session.void_sale(1)
    with pytest.raises(PosError):
        configured_session.correct_sale(
            seq=1,
            line_items=[_line(configured_session, "Mug", 1)],
            tenders=[Tender(CASH, Decimal("60"), tendered=Decimal("60"))],
        )


def test_get_missing_sale_raises(configured_session):
    with pytest.raises(PosError):
        configured_session.get_sale(99)
