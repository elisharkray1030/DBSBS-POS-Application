"""03 — Voucher & Octopus tenders + split settlement.

Cash and vouchers may be combined freely; Octopus always settles the full
sale amount on its own. Invalid settlements are rejected.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from pos.domain import (
    CASH,
    OCTOPUS,
    VOUCHER,
    InvalidSettlement,
    SaleNotFound,
    Tender,
)


def test_sale_can_be_settled_by_voucher_alone(configured_session):
    configured_session.add_item_to_sale("MUG", 1)
    result = configured_session.settle_current_sale([Tender(VOUCHER, Decimal("60"))])
    assert result.change_due == Decimal("0")
    sale = configured_session.get_sale(1)
    assert sale.tender_sum(VOUCHER) == Decimal("60")
    assert sale.tender_sum(CASH) == Decimal("0")
    assert sale.tender_sum(OCTOPUS) == Decimal("0")


def test_sale_can_be_settled_by_octopus_alone(configured_session):
    configured_session.add_item_to_sale("MUG", 1)
    result = configured_session.settle_current_sale([Tender(OCTOPUS, Decimal("60"))])
    assert result.change_due == Decimal("0")
    sale = configured_session.get_sale(1)
    assert sale.tender_sum(OCTOPUS) == Decimal("60")


def test_cash_and_voucher_split_in_any_combination(configured_session):
    configured_session.add_item_to_sale("MUG", 1)
    configured_session.add_item_to_sale("BDG", 2)  # 60 + 30 = 90
    configured_session.settle_current_sale(
        [
            Tender(CASH, Decimal("40"), tendered=Decimal("50")),
            Tender(VOUCHER, Decimal("50")),
        ]
    )
    sale = configured_session.get_sale(1)
    assert sale.tender_sum(CASH) == Decimal("40")
    assert sale.tender_sum(VOUCHER) == Decimal("50")


def test_voucher_covers_entire_sale_without_change(configured_session):
    configured_session.add_item_to_sale("MUG", 2)
    result = configured_session.settle_current_sale(
        [Tender(VOUCHER, Decimal("120"))]
    )
    assert result.change_due == Decimal("0")


def test_partial_octopus_is_rejected(configured_session):
    configured_session.add_item_to_sale("MUG", 2)  # 120
    with pytest.raises(InvalidSettlement):
        configured_session.settle_current_sale([Tender(OCTOPUS, Decimal("60"))])


def test_octopus_combined_with_any_other_method_is_rejected(configured_session):
    configured_session.add_item_to_sale("MUG", 1)  # 60
    with pytest.raises(InvalidSettlement):
        configured_session.settle_current_sale(
            [
                Tender(OCTOPUS, Decimal("30")),
                Tender(CASH, Decimal("30"), tendered=Decimal("30")),
            ]
        )
    configured_session.begin_sale()
    configured_session.add_item_to_sale("MUG", 1)
    with pytest.raises(InvalidSettlement):
        configured_session.settle_current_sale(
            [
                Tender(OCTOPUS, Decimal("60")),
                Tender(VOUCHER, Decimal("0")),
            ]
        )


def test_tenders_must_sum_to_the_sale_total(configured_session):
    configured_session.add_item_to_sale("MUG", 1)  # 60
    with pytest.raises(InvalidSettlement):
        configured_session.settle_current_sale([Tender(CASH, Decimal("50"), tendered=Decimal("50"))])
    with pytest.raises(InvalidSettlement):
        configured_session.settle_current_sale([Tender(CASH, Decimal("70"), tendered=Decimal("70"))])


def test_cash_tendered_less_than_cash_portion_is_rejected(configured_session):
    configured_session.add_item_to_sale("MUG", 1)  # 60
    with pytest.raises(InvalidSettlement):
        configured_session.settle_current_sale(
            [Tender(CASH, Decimal("60"), tendered=Decimal("50"))]
        )


def test_unknown_tender_method_is_rejected(configured_session):
    configured_session.add_item_to_sale("MUG", 1)
    with pytest.raises(InvalidSettlement):
        configured_session.settle_current_sale([Tender("crypto", Decimal("60"))])


def test_no_tenders_is_rejected(configured_session):
    configured_session.add_item_to_sale("MUG", 1)
    with pytest.raises(InvalidSettlement):
        configured_session.settle_current_sale([])


def test_non_finite_tender_amount_is_rejected(configured_session):
    configured_session.add_item_to_sale("MUG", 1)
    with pytest.raises(InvalidSettlement):
        configured_session.settle_current_sale([Tender(VOUCHER, Decimal("NaN"))])
    assert configured_session.current_sale_total() == Decimal("60")
    with pytest.raises(SaleNotFound):
        configured_session.get_sale(1)


def test_non_finite_cash_tendered_is_rejected(configured_session):
    configured_session.add_item_to_sale("MUG", 1)
    with pytest.raises(InvalidSettlement):
        configured_session.settle_current_sale(
            [Tender(CASH, Decimal("60"), tendered=Decimal("Infinity"))]
        )
    assert configured_session.current_sale_total() == Decimal("60")
    with pytest.raises(SaleNotFound):
        configured_session.get_sale(1)


def test_correct_sale_with_non_finite_tender_is_rejected(configured_session):
    configured_session.add_item_to_sale("MUG", 1)
    configured_session.settle_current_sale(
        [Tender(CASH, Decimal("60"), tendered=Decimal("60"))]
    )
    from tests.helpers import line_item

    with pytest.raises(InvalidSettlement):
        configured_session.correct_sale(
            seq=1,
            line_items=[line_item(configured_session, "Mug", 1)],
            tenders=[Tender(CASH, Decimal("NaN"), tendered=Decimal("NaN"))],
        )
    sale = configured_session.get_sale(1)
    assert sale.line_items[0].item_id == "MUG"
    assert sale.tender_sum(CASH) == Decimal("60")
