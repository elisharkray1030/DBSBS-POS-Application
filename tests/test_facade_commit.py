"""Commit-on-success settings mutations (spec #81, ticket 05).

Failed settings writes leave the running session at its prior state: a
candidate is persisted first, and the live settings adopt it only once the
device database accepts it. In particular a failed export-metadata save can
never make `wipe()` look safe.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from pos.domain import CASH, PersistenceError, PosError, Tender
from pos.facade import PosSession
from pos.persistence import InMemoryPersistence


class FailingSettingsStore(InMemoryPersistence):
    """An in-memory store that fails every settings write once armed."""

    def __init__(self) -> None:
        super().__init__()
        self.fail_saves = False

    def save_settings(self, settings) -> None:
        if self.fail_saves:
            raise PersistenceError("sabotaged settings write")
        super().save_settings(settings)


def test_failed_device_name_write_leaves_session_unchanged(clock):
    store = FailingSettingsStore()
    session = PosSession(store, clock=clock)
    session.set_device_name("Till A")
    store.fail_saves = True
    with pytest.raises(PersistenceError):
        session.set_device_name("Till B")
    assert session.device_name() == "Till A"


def test_failed_float_write_leaves_session_unchanged(clock):
    store = FailingSettingsStore()
    session = PosSession(store, clock=clock)
    session.set_float(500)
    store.fail_saves = True
    with pytest.raises(PersistenceError):
        session.set_float(600)
    assert session.float_amount() == Decimal("500")


def test_failed_catalog_write_leaves_previous_catalog_active(clock, tmp_path):
    store = FailingSettingsStore()
    session = PosSession(store, clock=clock)
    first = tmp_path / "first.csv"
    first.write_text(
        "ItemID,ItemName,Price,Inventory,Sales,Revenue\n"
        "MUG,Mug,60,20,30,1800\n",
        encoding="utf-8",
    )
    second = tmp_path / "second.csv"
    second.write_text(
        "ItemID,ItemName,Price,Inventory,Sales,Revenue\n"
        "BDG,Badge,15,50,10,150\n",
        encoding="utf-8",
    )
    session.load_catalog(first)
    store.fail_saves = True
    with pytest.raises(PersistenceError):
        session.load_catalog(second)
    assert [i.item_id for i in session.list_items()] == ["MUG"]


def test_failed_sold_out_write_leaves_previous_state(clock, catalog_file):
    store = FailingSettingsStore()
    session = PosSession(store, clock=clock)
    session.set_device_name("Till A")
    session.set_float(500)
    session.load_catalog(catalog_file)
    session.mark_sold_out("MUG")
    store.fail_saves = True
    with pytest.raises(PersistenceError):
        session.unmark_sold_out("MUG")
    assert session.is_sold_out("MUG") is True


def test_failed_export_metadata_save_leaves_wipe_blocked(clock, catalog_file, tmp_path):
    store = FailingSettingsStore()
    session = PosSession(store, clock=clock)
    session.set_device_name("Till A")
    session.set_float(500)
    session.load_catalog(catalog_file)
    session.add_item_to_sale("MUG", 1)
    session.settle_current_sale([Tender(CASH, Decimal("60"), tendered=Decimal("60"))])

    store.fail_saves = True
    with pytest.raises(PersistenceError):
        session.export_csv(tmp_path)

    # The running session must not consider itself exported.
    with pytest.raises(PosError, match="Wipe blocked"):
        session.wipe()

    # Reopening the device must reach the same wipe decision.
    reopened = PosSession(store, clock=clock)
    with pytest.raises(PosError, match="Wipe blocked"):
        reopened.wipe()


def test_failed_export_metadata_save_keeps_prior_export_date(
    clock, catalog_file, tmp_path
):
    store = FailingSettingsStore()
    session = PosSession(store, clock=clock)
    session.set_device_name("Till A")
    session.set_float(500)
    session.load_catalog(catalog_file)
    session.add_item_to_sale("MUG", 1)
    session.settle_current_sale([Tender(CASH, Decimal("60"), tendered=Decimal("60"))])
    session.export_csv(tmp_path)  # first export succeeds and is recorded
    clock.advance(minutes=5)
    session.add_item_to_sale("MUG", 1)
    session.settle_current_sale([Tender(CASH, Decimal("60"), tendered=Decimal("60"))])

    store.fail_saves = True
    with pytest.raises(PersistenceError):
        session.export_csv(tmp_path)
    # The prior export timestamp still stands, so the pre-failure sale is safe.
    with pytest.raises(PosError, match="Wipe blocked"):
        session.wipe()
