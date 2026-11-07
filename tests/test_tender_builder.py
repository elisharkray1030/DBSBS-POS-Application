from decimal import Decimal

from pos.domain import CASH, VOUCHER, Tender
from pos.ui.dialogs import build_cash_voucher_tenders


def test_cash_voucher_tenders_derive_cash_from_voucher_and_total():
    tenders = build_cash_voucher_tenders(
        Decimal("90"), Decimal("50"), Decimal("50")
    )

    assert tenders == [
        Tender(CASH, Decimal("40"), tendered=Decimal("50")),
        Tender(VOUCHER, Decimal("50")),
    ]
