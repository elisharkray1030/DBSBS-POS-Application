from decimal import Decimal

from pos.domain import CASH, OCTOPUS, VOUCHER, Tender
from pos.ui.dialogs import build_selected_tenders


def test_build_selected_tenders_keeps_cash_portion_separate_from_tendered():
    tenders = build_selected_tenders(
        {CASH: Decimal("40"), VOUCHER: Decimal("50")}, Decimal("50")
    )

    assert tenders == [
        Tender(CASH, Decimal("40"), tendered=Decimal("50")),
        Tender(VOUCHER, Decimal("50")),
    ]


def test_build_selected_tenders_supports_all_three_methods():
    tenders = build_selected_tenders(
        {
            CASH: Decimal("40"),
            OCTOPUS: Decimal("20"),
            VOUCHER: Decimal("30"),
        },
        Decimal("50"),
    )

    assert tenders == [
        Tender(CASH, Decimal("40"), tendered=Decimal("50")),
        Tender(OCTOPUS, Decimal("20")),
        Tender(VOUCHER, Decimal("30")),
    ]


def test_build_selected_tenders_supports_methods_without_cash():
    tenders = build_selected_tenders(
        {OCTOPUS: Decimal("30"), VOUCHER: Decimal("30")}, None
    )

    assert tenders == [
        Tender(OCTOPUS, Decimal("30")),
        Tender(VOUCHER, Decimal("30")),
    ]
