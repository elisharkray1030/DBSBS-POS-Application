"""The one SQLite round-trip sanity test the spec allows (docs/spec.md §Testing).

Everything else is tested through the facade with InMemoryPersistence. This
single test exercises the real SQLite backing the way the production app uses
it, including a simulated crash (connections left open, no graceful close).
"""

from __future__ import annotations

from decimal import Decimal

from pos.domain import CASH, Tender
from pos.facade import PosSession


def test_sqlite_backing_round_trips_and_wipe(
    sqlite_store_factory, clock, catalog_file, tmp_path
):
    store = sqlite_store_factory()
    session = PosSession(store, clock=clock)
    session.set_device_name("Till A")
    session.set_float(500)
    session.load_catalog(catalog_file)
    session.mark_sold_out("Badge")
    session.add_item_to_sale("Mug", 2)
    session.settle_current_sale(
        [Tender(CASH, Decimal("120"), tendered=Decimal("200"))]
    )
    session.record_cash_adjustment(100, "Topping up change")

    # Simulate a crash: no graceful close, just open the same file again.
    reopened_store = sqlite_store_factory()
    reopened = PosSession(reopened_store, clock=clock)
    assert reopened.is_configured() is True
    assert reopened.device_name() == "Till A"
    assert reopened.float_amount() == Decimal("500")
    assert reopened.is_sold_out("Badge") is True
    sale = reopened.get_sale(1)
    assert sale.total == Decimal("120")
    assert sale.line_items[0].quantity == 2
    assert reopened.running_summary().takings == Decimal("120")
    assert reopened.list_cash_adjustments()[0].reason == "Topping up change"

    # The end-of-day export must be taken before the wipe.
    session.export_csv(tmp_path)
    session.wipe()
    assert session.is_configured() is False
    assert session.list_sales() == []
