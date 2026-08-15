"""09 — Wipe at end of event.

A deliberate action wipes the local database so next year's event starts from
a blank slate. The wipe is blocked until the end-of-day export has been taken;
after wiping, the app is back at the setup screen as if new. Confirmation is
enforced at the UI layer.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from pos.domain import CASH, PosError, Tender


def _sell(configured_session):
    configured_session.add_item_to_sale("Mug", 1)
    configured_session.settle_current_sale(
        [Tender(CASH, Decimal("60"), tendered=Decimal("60"))]
    )


def test_wipe_blocked_until_the_export_is_taken(configured_session, tmp_path):
    _sell(configured_session)
    with pytest.raises(PosError):
        configured_session.wipe()
    configured_session.export_csv(tmp_path)
    configured_session.wipe()
    assert configured_session.is_configured() is False


def test_wipe_clears_sales_adjustments_catalog_and_settings(
    configured_session, tmp_path
):
    _sell(configured_session)
    configured_session.record_cash_adjustment(100, "Topping up change")
    configured_session.export_csv(tmp_path)

    configured_session.wipe()

    assert configured_session.is_configured() is False
    assert configured_session.list_sales() == []
    assert configured_session.list_voids() == []
    assert configured_session.list_cash_adjustments() == []
    assert configured_session.list_items() == []
    assert configured_session.device_name() == ""
    assert configured_session.float_amount() is None


def test_wipe_returns_to_setup_as_if_new(configured_session, catalog_file, tmp_path):
    _sell(configured_session)
    configured_session.export_csv(tmp_path)
    configured_session.wipe()

    configured_session.set_device_name("Till B")
    configured_session.set_float(300)
    configured_session.load_catalog(catalog_file)
    assert configured_session.is_configured() is True


def test_wipe_blocked_after_a_sale_made_following_the_export(
    configured_session, tmp_path, clock
):
    _sell(configured_session)
    configured_session.export_csv(tmp_path)
    clock.advance(minutes=10)
    configured_session.add_item_to_sale("Badge", 1)
    configured_session.settle_current_sale(
        [Tender(CASH, Decimal("15"), tendered=Decimal("15"))]
    )
    with pytest.raises(PosError):
        configured_session.wipe()
    configured_session.export_csv(tmp_path)
    configured_session.wipe()
    assert configured_session.is_configured() is False


def test_sequence_numbers_restart_after_wipe(configured_session, catalog_file, tmp_path):
    _sell(configured_session)
    configured_session.export_csv(tmp_path)
    configured_session.wipe()

    configured_session.set_device_name("Till A")
    configured_session.set_float(500)
    configured_session.load_catalog(catalog_file)
    configured_session.add_item_to_sale("Mug", 1)
    result = configured_session.settle_current_sale(
        [Tender(CASH, Decimal("60"), tendered=Decimal("60"))]
    )
    assert result.seq == 1
