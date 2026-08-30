"""01 — Walking skeleton + setup.

The facade is the single seam. A session starts unconfigured; setting the
device name, float, and catalog configures it. All of it persists, so a new
session over the same store sees it again.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from pos.domain import CatalogError, InvalidMoney, ItemStock, SetupError
from pos.facade import PosSession
from pos.persistence import InMemoryPersistence


def test_session_starts_unconfigured(session):
    assert session.is_configured() is False


def test_device_name_required(session):
    with pytest.raises(SetupError):
        session.set_device_name("   ")
    session.set_device_name("Till B")
    assert session.device_name() == "Till B"


def test_float_rejects_negative(session):
    with pytest.raises(SetupError):
        session.set_float(-1)
    session.set_float("0")
    assert session.float_amount() == Decimal("0")


def test_float_rejects_non_finite(session):
    with pytest.raises(InvalidMoney):
        session.set_float(Decimal("NaN"))
    with pytest.raises(InvalidMoney):
        session.set_float("Infinity")
    assert session.float_amount() is None


def test_catalog_loads_items_with_prices_and_quantities(session, catalog_file):
    count = session.load_catalog(catalog_file)
    assert count == 3
    items = session.list_items()
    assert [i.item_id for i in items] == ["MUG", "BDG", "PLUSH"]
    assert [i.name for i in items] == ["Mug", "Badge", "Plush Bear"]
    assert items[0].price == Decimal("60")
    assert items[0].starting_quantity == 20
    assert items[2].starting_quantity is None
    assert all(isinstance(i, ItemStock) for i in items)


def test_configured_once_everything_is_set(session, catalog_file):
    session.set_device_name("Till A")
    assert session.is_configured() is False
    session.set_float(500)
    assert session.is_configured() is False
    session.load_catalog(catalog_file)
    assert session.is_configured() is True


def test_settings_survive_reopen_over_in_memory_store(clock):
    store = InMemoryPersistence()
    first = PosSession(store, clock=clock)
    first.set_device_name("Till A")
    first.set_float(500)

    reopened = PosSession(store, clock=clock)
    assert reopened.device_name() == "Till A"
    assert reopened.float_amount() == Decimal("500")


def test_catalog_csv_must_have_a_header(session, tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("Mug,60,20\n", encoding="utf-8")
    with pytest.raises(CatalogError):
        session.load_catalog(bad)


def test_catalog_retains_item_identity_after_import(configured_session):
    items = configured_session.list_items()
    assert all(isinstance(i.item_id, str) and i.item_id for i in items)
    assert len({i.item_id for i in items}) == len(items)
