"""Facade-level tests against the real SQLite backing.

Storage concerns live in the adapter-seam storage suite
(test_sqlite_storage.py); this file keeps the facade-level round-trips — the
way the production app uses the device database, including a simulated crash
(connections left open, no graceful close) and legacy-database migration
through the session.
"""

from __future__ import annotations

import csv
from decimal import Decimal

from pos.domain import CASH, Tender
from pos.facade import PosSession


def _read_rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.reader(handle))


def test_pre_source_cells_database_is_migrated(sqlite_store_factory, clock, tmp_path):
    legacy = tmp_path / "legacy.db"
    import sqlite3

    conn = sqlite3.connect(legacy)
    conn.executescript(
        """
        CREATE TABLE settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE catalog (
            item_id           TEXT PRIMARY KEY,
            name              TEXT NOT NULL,
            price             TEXT NOT NULL,
            starting_quantity INTEGER,
            sold_out          INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    conn.execute(
        "INSERT INTO catalog (item_id, name, price, starting_quantity, sold_out)"
        " VALUES ('MUG', 'Mug', '60', 20, 0)"
    )
    conn.commit()
    conn.close()

    from pos.sqlite import SqlitePersistence

    store = SqlitePersistence(legacy)
    session = PosSession(store, clock=clock)
    session.set_device_name("Till A")
    session.set_float(500)
    report = [p for p in session.export_csv(tmp_path) if p.name.startswith("stocks-")]
    assert len(report) == 1
    rows = _read_rows(report[0])
    assert rows[1] == ["MUG", "Mug", "60", "20", "0", "0"]
    store.close()


def test_legacy_raw_cells_are_backfilled_into_source_cells(
    sqlite_store_factory, clock, tmp_path
):
    legacy = tmp_path / "legacy.db"
    import sqlite3

    conn = sqlite3.connect(legacy)
    conn.executescript(
        """
        CREATE TABLE settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE catalog (
            item_id           TEXT PRIMARY KEY,
            name              TEXT NOT NULL,
            price             TEXT NOT NULL,
            starting_quantity INTEGER,
            sold_out          INTEGER NOT NULL DEFAULT 0,
            raw_cells         TEXT
        );
        """
    )
    conn.execute(
        "INSERT INTO catalog (item_id, name, price, starting_quantity, sold_out, raw_cells)"
        " VALUES ('MUG', 'Mug', '60', 20, 0, '[\"MUG\", \"  Mug  \", \"60.00\", \"020\"]')"
    )
    conn.commit()
    conn.close()

    from pos.facade import PosSession
    from pos.sqlite import SqlitePersistence

    store = SqlitePersistence(legacy)
    session = PosSession(store, clock=clock)
    session.set_device_name("Till A")
    session.set_float(500)
    report = [p for p in session.export_csv(tmp_path) if p.name.startswith("stocks-")]
    assert len(report) == 1
    rows = _read_rows(report[0])
    assert rows[1] == ["MUG", "  Mug  ", "60.00", "020", "0", "0"]
    store.close()


def test_sqlite_backing_round_trips_and_wipe(
    sqlite_store_factory, clock, catalog_file, tmp_path
):
    messy = tmp_path / "messy.csv"
    messy.write_text(
        "ItemID,ItemName,Price,Inventory,Sales,Revenue\n"
        "MUG, Mug ,60.00,020,30,1800\n"
        "BDG,Badge,15,50,10,150\n"
        "PLUSH,Plush Bear,120,,5,600\n",
        encoding="utf-8",
    )
    store = sqlite_store_factory()
    session = PosSession(store, clock=clock)
    session.set_device_name("Till A")
    session.set_float(500)
    session.load_catalog(messy)
    session.mark_sold_out("BDG")
    session.add_item_to_sale("MUG", 2)
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
    assert reopened.is_sold_out("BDG") is True
    sale = reopened.get_sale(1)
    assert sale.total == Decimal("120")
    assert sale.line_items[0].quantity == 2
    assert reopened.running_summary().takings == Decimal("120")
    assert reopened.list_cash_adjustments()[0].reason == "Topping up change"

    # Raw cells survive the reopen: the report still echoes the master file.
    report = [p for p in reopened.export_csv(tmp_path) if p.name.startswith("stocks-")]
    assert len(report) == 1
    rows = _read_rows(report[0])
    assert rows[1] == ["MUG", " Mug ", "60.00", "020", "2", "120.00"]
    assert rows[2] == ["BDG", "Badge", "15", "50", "0", "0"]
    assert rows[3] == ["PLUSH", "Plush Bear", "120", "", "0", "0"]

    # The end-of-day export must be taken before the wipe.
    session.export_csv(tmp_path)
    session.wipe()
    assert session.is_configured() is False
    assert session.list_sales() == []
