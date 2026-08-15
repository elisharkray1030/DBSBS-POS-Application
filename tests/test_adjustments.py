"""06 — Cash adjustments + running summary.

Cash added to or removed from the till mid-day is recorded with a reason;
expected cash reflects float + cash sales + added − removed. Cash adjustments
are not sales. The running summary excludes voids.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from pos.domain import CASH, PosError, Tender


def settle(configured_session, item, qty, amount):
    configured_session.add_item_to_sale(item, qty)
    configured_session.settle_current_sale([Tender(CASH, amount, tendered=amount)])


def test_cash_addition_is_recorded_with_time_and_reason(configured_session, clock):
    clock.advance(minutes=90)
    configured_session.record_cash_adjustment(200, "Topping up change")
    adjustments = configured_session.list_cash_adjustments()
    assert len(adjustments) == 1
    assert adjustments[0].amount == Decimal("200")
    assert adjustments[0].reason == "Topping up change"
    assert adjustments[0].created_at == clock.now


def test_cash_removal_is_recorded_with_time_and_reason(configured_session):
    configured_session.record_cash_adjustment(-50, "Removing excess notes")
    adjustments = configured_session.list_cash_adjustments()
    assert adjustments[0].amount == Decimal("-50")


def test_expected_cash_reflects_float_plus_sales_and_adjustments(configured_session):
    settle(configured_session, "Mug", 1, Decimal("60"))
    settle(configured_session, "Badge", 2, Decimal("30"))
    configured_session.record_cash_adjustment(200, "Topping up change")
    configured_session.record_cash_adjustment(-50, "Removing excess notes")
    end_of_day = configured_session.end_of_day()
    assert end_of_day.expected_cash == Decimal("500") + Decimal("90") + Decimal("150")


def test_running_summary_excludes_voids(configured_session):
    settle(configured_session, "Mug", 1, Decimal("60"))
    settle(configured_session, "Badge", 1, Decimal("15"))
    configured_session.void_sale(1)
    summary = configured_session.running_summary()
    assert summary.takings == Decimal("15")
    assert summary.sale_count == 1


def test_running_summary_reflects_corrections_final_state(configured_session):
    settle(configured_session, "Mug", 1, Decimal("60"))
    from tests.helpers import line_item

    configured_session.correct_sale(
        seq=1,
        line_items=[line_item(configured_session, "Badge", 4)],
        tenders=[Tender(CASH, Decimal("60"), tendered=Decimal("60"))],
    )
    summary = configured_session.running_summary()
    assert summary.takings == Decimal("60")
    assert summary.sale_count == 1


def test_cash_adjustments_are_not_sales(configured_session):
    configured_session.record_cash_adjustment(200, "Topping up change")
    summary = configured_session.running_summary()
    assert summary.sale_count == 0
    assert summary.takings == Decimal("0")
    assert len(configured_session.list_sales()) == 0


def test_zero_adjustment_rejected(configured_session):
    with pytest.raises(PosError):
        configured_session.record_cash_adjustment(0, "no-op")


def test_adjustment_requires_a_reason(configured_session):
    with pytest.raises(PosError):
        configured_session.record_cash_adjustment(100, "   ")
