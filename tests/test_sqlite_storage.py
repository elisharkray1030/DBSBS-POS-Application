"""Adapter-seam storage suite for the device database (umbrella U3).

Storage concerns — schema shape, the migration ladder, corruption, the
upsert-by-sequence contract, and wipe — are tested directly against the
concrete SQLite adapter, which is the seam at which they are observable. The
facade round-trip stays in test_sqlite_roundtrip.py.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from decimal import Decimal

import pytest

from pos.domain import (
    CASH,
    COMPLETED,
    CashAdjustment,
    CorruptRecordError,
    Item,
    LineItem,
    PersistenceError,
    Sale,
    Settings,
    Tender,
    money,
)
from pos.sqlite import SqlitePersistence
from pos.sqlite_schema import LATEST_VERSION

_SALES_SUMMARY = """
            total       TEXT NOT NULL,
            cash        TEXT NOT NULL,
            octopus     TEXT NOT NULL,
            voucher     TEXT NOT NULL,
"""


def _legacy_db(path, catalog_schema: str, sales_schema: str = "") -> None:
    """Create a legacy device database with the given catalog column set."""
    conn = sqlite3.connect(path)
    conn.executescript(
        f"""
        CREATE TABLE settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE catalog (
            {catalog_schema}
        );
        CREATE TABLE sales (
            seq         INTEGER PRIMARY KEY,
            status      TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL,
            device_name TEXT NOT NULL,
            {sales_schema}
            line_items  TEXT NOT NULL,
            tenders     TEXT NOT NULL
        );
        CREATE TABLE cash_adjustments (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            amount     TEXT NOT NULL,
            reason     TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    conn.commit()
    conn.close()


@pytest.fixture
def adapter(tmp_path):
    adapters = []

    def factory():
        store = SqlitePersistence(tmp_path / "pos.db")
        adapters.append(store)
        return store

    yield factory
    for store in adapters:
        store.close()


# -- schema shape ----------------------------------------------------------


def test_fresh_database_is_created_at_the_latest_schema(adapter):
    db = adapter()
    version = db._conn.execute("PRAGMA user_version").fetchone()[0]
    assert version == LATEST_VERSION
    tables = {
        row["name"]
        for row in db._conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    assert {"settings", "catalog", "sales", "cash_adjustments"} <= tables


def test_fresh_database_has_no_sale_summary_columns(adapter):
    db = adapter()
    columns = {
        row["name"] for row in db._conn.execute("PRAGMA table_info(sales)")
    }
    assert {"total", "cash", "octopus", "voucher"}.isdisjoint(columns)


# -- migration ladder ------------------------------------------------------


def test_pre_source_cells_database_is_migrated(adapter, tmp_path):
    legacy = tmp_path / "legacy.db"
    _legacy_db(
        legacy,
        catalog_schema="""
        item_id           TEXT PRIMARY KEY,
        name              TEXT NOT NULL,
        price             TEXT NOT NULL,
        starting_quantity INTEGER,
        sold_out          INTEGER NOT NULL DEFAULT 0
        """,
    )
    conn = sqlite3.connect(legacy)
    conn.execute(
        "INSERT INTO catalog (item_id, name, price, starting_quantity, sold_out)"
        " VALUES ('MUG', 'Mug', '60', 20, 0)"
    )
    conn.commit()
    conn.close()

    db = SqlitePersistence(legacy)
    try:
        version = db._conn.execute("PRAGMA user_version").fetchone()[0]
        assert version == LATEST_VERSION
        columns = {
            row["name"] for row in db._conn.execute("PRAGMA table_info(catalog)")
        }
        assert "source_cells" in columns
        settings = db.load_settings()
        assert settings is not None
        assert settings.catalog[0].item_id == "MUG"
    finally:
        db.close()


def test_raw_cells_database_is_backfilled_into_source_cells(adapter, tmp_path):
    legacy = tmp_path / "legacy.db"
    _legacy_db(
        legacy,
        catalog_schema="""
        item_id           TEXT PRIMARY KEY,
        name              TEXT NOT NULL,
        price             TEXT NOT NULL,
        starting_quantity INTEGER,
        sold_out          INTEGER NOT NULL DEFAULT 0,
        raw_cells         TEXT
        """,
    )
    conn = sqlite3.connect(legacy)
    conn.execute(
        "INSERT INTO catalog (item_id, name, price, starting_quantity, sold_out, raw_cells)"
        " VALUES ('MUG', 'Mug', '60', 20, 0, '[\"MUG\", \"  Mug  \", \"60.00\", \"020\"]')"
    )
    conn.commit()
    conn.close()

    db = SqlitePersistence(legacy)
    try:
        version = db._conn.execute("PRAGMA user_version").fetchone()[0]
        assert version == LATEST_VERSION
        columns = {
            row["name"] for row in db._conn.execute("PRAGMA table_info(catalog)")
        }
        assert "source_cells" in columns
        assert "raw_cells" not in columns
        settings = db.load_settings()
        assert settings.source_cells["MUG"] == ("MUG", "  Mug  ", "60.00", "020")
    finally:
        db.close()


def test_current_schema_database_without_version_stamp_is_upgraded_in_place(
    adapter, tmp_path
):
    legacy = tmp_path / "legacy.db"
    _legacy_db(
        legacy,
        catalog_schema="""
        item_id           TEXT PRIMARY KEY,
        name              TEXT NOT NULL,
        price             TEXT NOT NULL,
        starting_quantity INTEGER,
        sold_out          INTEGER NOT NULL DEFAULT 0,
        source_cells      TEXT
        """,
        sales_schema=_SALES_SUMMARY,
    )
    conn = sqlite3.connect(legacy)
    conn.execute(
        "INSERT INTO catalog (item_id, name, price, starting_quantity, sold_out, source_cells)"
        " VALUES ('MUG', 'Mug', '60', 20, 0, '[\"MUG\", \"Mug\", \"60\", \"20\"]')"
    )
    conn.commit()
    conn.close()

    db = SqlitePersistence(legacy)
    try:
        version = db._conn.execute("PRAGMA user_version").fetchone()[0]
        assert version == LATEST_VERSION
        settings = db.load_settings()
        assert settings.source_cells["MUG"] == ("MUG", "Mug", "60", "20")
        sales_columns = {
            row["name"] for row in db._conn.execute("PRAGMA table_info(sales)")
        }
        assert {"total", "cash", "octopus", "voucher"}.isdisjoint(sales_columns)
    finally:
        db.close()


# -- sale round-trip and upsert --------------------------------------------


def _sale(seq: int, quantity: int) -> Sale:
    now = datetime(2026, 8, 15, 9, 0, 0)
    return Sale(
        seq=seq,
        created_at=now,
        updated_at=now,
        status=COMPLETED,
        line_items=[
            LineItem(item_id="MUG", item_name="Mug", quantity=quantity, price=money("60"))
        ],
        tenders=[
            Tender(CASH, money(str(60 * quantity)), tendered=money(str(60 * quantity)))
        ],
        device_name="Till A",
    )


def test_sale_round_trips_with_figures_derived_from_its_record(adapter):
    db = adapter()
    db.save_sale(_sale(1, 2))
    got = db.get_sales()
    assert len(got) == 1
    assert got[0].seq == 1
    assert got[0].total == Decimal("120")
    assert got[0].tender_sum("cash") == Decimal("120")
    assert got[0].line_items[0].quantity == 2


def test_saving_by_sequence_upserts_instead_of_duplicating(adapter):
    db = adapter()
    db.save_sale(_sale(1, 2))
    db.save_sale(_sale(1, 3))
    sales = db.get_sales()
    assert len(sales) == 1
    assert sales[0].line_items[0].quantity == 3


# -- corruption and error wrapping -----------------------------------------


def test_corrupt_sale_names_its_sequence_number(adapter):
    db = adapter()
    db._conn.execute(
        "INSERT INTO sales (seq, status, created_at, updated_at, device_name,"
        " line_items, tenders)"
        " VALUES (7, 'completed', '2026-08-15T09:00:00', '2026-08-15T09:00:00',"
        " 'Till A', 'not json', '[]')"
    )
    db._conn.commit()
    with pytest.raises(CorruptRecordError, match="7"):
        db.get_sales()


def test_corrupt_tenders_json_raise_corrupt_record_error(adapter):
    db = adapter()
    db._conn.execute(
        "INSERT INTO sales (seq, status, created_at, updated_at, device_name,"
        " line_items, tenders)"
        " VALUES (1, 'completed', '2026-08-15T09:00:00', '2026-08-15T09:00:00',"
        " 'Till A', '[{\"item_id\": \"MUG\", \"item_name\": \"Mug\","
        " \"quantity\": 2, \"price\": \"60\"}]', '{broken')"
    )
    db._conn.commit()
    with pytest.raises(CorruptRecordError):
        db.get_sales()


def test_non_list_line_items_json_raises_corrupt_record_error(adapter):
    db = adapter()
    db._conn.execute(
        "INSERT INTO sales (seq, status, created_at, updated_at, device_name,"
        " line_items, tenders)"
        " VALUES (3, 'completed', '2026-08-15T09:00:00',"
        " '2026-08-15T09:00:00', 'Till A', '{\"not\": \"a list\"}', '[]')"
    )
    db._conn.commit()
    with pytest.raises(CorruptRecordError, match="3"):
        db.get_sales()


def test_corrupt_cash_adjustment_raises_corrupt_record_error(adapter):
    db = adapter()
    db._conn.execute(
        "INSERT INTO cash_adjustments (amount, reason, created_at)"
        " VALUES ('oops', 'Topping up change', '2026-08-15T09:30:00')"
    )
    db._conn.commit()
    with pytest.raises(CorruptRecordError):
        db.get_cash_adjustments()


def test_corrupt_settings_value_raises_corrupt_record_error(adapter):
    db = adapter()
    db._conn.execute(
        "INSERT INTO settings (key, value) VALUES ('float', 'not-a-number')"
    )
    db._conn.commit()
    with pytest.raises(CorruptRecordError):
        db.load_settings()


def test_unknown_sale_status_raises_corrupt_record_error(adapter):
    db = adapter()
    db._conn.execute(
        "INSERT INTO sales (seq, status, created_at, updated_at, device_name,"
        " line_items, tenders)"
        " VALUES (1, 'cancelled', '2026-08-15T09:00:00', '2026-08-15T09:00:00',"
        " 'Till A', '[{\"item_id\": \"MUG\", \"item_name\": \"Mug\","
        " \"quantity\": 1, \"price\": \"60\"}]',"
        " '[{\"method\": \"cash\", \"amount\": \"60\", \"tendered\": \"60\"}]')"
    )
    db._conn.commit()
    with pytest.raises(CorruptRecordError, match="status"):
        db.get_sales()


def test_unknown_tender_method_raises_corrupt_record_error(adapter):
    db = adapter()
    db._conn.execute(
        "INSERT INTO sales (seq, status, created_at, updated_at, device_name,"
        " line_items, tenders)"
        " VALUES (1, 'completed', '2026-08-15T09:00:00', '2026-08-15T09:00:00',"
        " 'Till A', '[{\"item_id\": \"MUG\", \"item_name\": \"Mug\","
        " \"quantity\": 1, \"price\": \"60\"}]',"
        " '[{\"method\": \"card\", \"amount\": \"60\"}]')"
    )
    db._conn.commit()
    with pytest.raises(CorruptRecordError, match="method"):
        db.get_sales()


def test_non_string_line_item_identifier_raises_corrupt_record_error(adapter):
    db = adapter()
    db._conn.execute(
        "INSERT INTO sales (seq, status, created_at, updated_at, device_name,"
        " line_items, tenders)"
        " VALUES (1, 'completed', '2026-08-15T09:00:00', '2026-08-15T09:00:00',"
        " 'Till A', '[{\"item_id\": 123, \"item_name\": \"Mug\","
        " \"quantity\": 1, \"price\": \"60\"}]',"
        " '[{\"method\": \"cash\", \"amount\": \"60\", \"tendered\": \"60\"}]')"
    )
    db._conn.commit()
    with pytest.raises(CorruptRecordError, match="item id"):
        db.get_sales()


def test_non_string_line_item_name_raises_corrupt_record_error(adapter):
    db = adapter()
    db._conn.execute(
        "INSERT INTO sales (seq, status, created_at, updated_at, device_name,"
        " line_items, tenders)"
        " VALUES (1, 'completed', '2026-08-15T09:00:00', '2026-08-15T09:00:00',"
        " 'Till A', '[{\"item_id\": \"MUG\", \"item_name\": 123,"
        " \"quantity\": 1, \"price\": \"60\"}]',"
        " '[{\"method\": \"cash\", \"amount\": \"60\", \"tendered\": \"60\"}]')"
    )
    db._conn.commit()
    with pytest.raises(CorruptRecordError, match="item name"):
        db.get_sales()


def test_empty_device_name_raises_corrupt_record_error(adapter):
    db = adapter()
    db._conn.execute(
        "INSERT INTO sales (seq, status, created_at, updated_at, device_name,"
        " line_items, tenders)"
        " VALUES (1, 'completed', '2026-08-15T09:00:00', '2026-08-15T09:00:00',"
        " '', '[{\"item_id\": \"MUG\", \"item_name\": \"Mug\","
        " \"quantity\": 1, \"price\": \"60\"}]',"
        " '[{\"method\": \"cash\", \"amount\": \"60\", \"tendered\": \"60\"}]')"
    )
    db._conn.commit()
    with pytest.raises(CorruptRecordError, match="device name"):
        db.get_sales()


def test_empty_catalog_name_raises_corrupt_record_error(adapter):
    db = adapter()
    db._conn.execute(
        "INSERT INTO catalog (item_id, name, price)"
        " VALUES ('MUG', '', '60')"
    )
    db._conn.commit()
    with pytest.raises(CorruptRecordError, match="name"):
        db.load_settings()


def test_empty_catalog_item_id_raises_corrupt_record_error(adapter):
    db = adapter()
    db._conn.execute(
        "INSERT INTO catalog (item_id, name, price)"
        " VALUES ('', 'Mug', '60')"
    )
    db._conn.commit()
    with pytest.raises(CorruptRecordError, match="item id"):
        db.load_settings()


def test_corrupt_catalog_price_raises_corrupt_record_error(adapter):
    db = adapter()
    db._conn.execute(
        "INSERT INTO catalog (item_id, name, price) VALUES ('MUG', 'Mug', 'oops')"
    )
    db._conn.commit()
    with pytest.raises(CorruptRecordError):
        db.load_settings()


def test_non_integer_starting_quantity_raises_corrupt_record_error(adapter):
    db = adapter()
    db._conn.execute(
        "INSERT INTO catalog (item_id, name, price, starting_quantity)"
        " VALUES ('MUG', 'Mug', '60', 'abc')"
    )
    db._conn.commit()
    with pytest.raises(CorruptRecordError, match="starting quantity"):
        db.load_settings()


def test_non_integer_sold_out_raises_corrupt_record_error(adapter):
    db = adapter()
    db._conn.execute(
        "INSERT INTO catalog (item_id, name, price, sold_out)"
        " VALUES ('MUG', 'Mug', '60', 'yes')"
    )
    db._conn.commit()
    with pytest.raises(CorruptRecordError, match="sold-out flag"):
        db.load_settings()


def test_out_of_range_sold_out_raises_corrupt_record_error(adapter):
    db = adapter()
    db._conn.execute(
        "INSERT INTO catalog (item_id, name, price, sold_out)"
        " VALUES ('MUG', 'Mug', '60', 2)"
    )
    db._conn.commit()
    with pytest.raises(CorruptRecordError, match="sold-out flag"):
        db.load_settings()


def test_corrupt_source_cells_raise_corrupt_record_error(adapter):
    db = adapter()
    db._conn.execute(
        "INSERT INTO catalog (item_id, name, price, source_cells)"
        " VALUES ('MUG', 'Mug', '60', '{broken')"
    )
    db._conn.commit()
    with pytest.raises(CorruptRecordError):
        db.load_settings()


def test_source_cells_of_wrong_shape_raise_corrupt_record_error(adapter):
    db = adapter()
    db._conn.execute(
        "INSERT INTO catalog (item_id, name, price, source_cells)"
        " VALUES ('MUG', 'Mug', '60', '[\"MUG\", \"Mug\"]')"
    )
    db._conn.commit()
    with pytest.raises(CorruptRecordError):
        db.load_settings()


def test_non_database_file_raises_persistence_error(tmp_path):
    bad = tmp_path / "bad.db"
    bad.write_text("this is not a sqlite database")
    with pytest.raises(PersistenceError):
        SqlitePersistence(bad)


# -- rollback and write atomicity on failure -------------------------------


def _settings_with(item_ids):
    return Settings(
        device_name="Till A",
        float_amount=Decimal("500"),
        catalog=[
            Item(item_id=item_id, name=item_id, price=Decimal("60"))
            for item_id in item_ids
        ],
    )


def test_failed_settings_catalog_save_rolls_back_to_prior_state(adapter):
    db = adapter()
    db.save_settings(_settings_with(["MUG", "BDG"]))
    db._conn.execute(
        "CREATE TRIGGER sabotage_catalog BEFORE INSERT ON catalog"
        " BEGIN SELECT RAISE(ABORT, 'sabotaged'); END;"
    )
    db._conn.commit()
    replacement = Settings(
        device_name="Till B",
        float_amount=Decimal("600"),
        catalog=[Item(item_id="PLUSH", name="Plush", price=Decimal("120"))],
    )
    with pytest.raises(PersistenceError):
        db.save_settings(replacement)
    after = db.load_settings()
    assert after is not None
    assert after.device_name == "Till A"
    assert after.float_amount == Decimal("500")
    assert [i.item_id for i in after.catalog] == ["MUG", "BDG"]


def test_failed_sale_write_leaves_no_partial_sale(adapter):
    db = adapter()
    db.save_sale(_sale(1, 2))
    db._conn.execute(
        "CREATE TRIGGER sabotage_sales BEFORE INSERT ON sales"
        " BEGIN SELECT RAISE(ABORT, 'sabotaged'); END;"
    )
    db._conn.commit()
    with pytest.raises(PersistenceError):
        db.save_sale(_sale(2, 1))
    assert [s.seq for s in db.get_sales()] == [1]


def test_failed_cash_adjustment_write_leaves_no_partial_adjustment(adapter):
    db = adapter()
    db.save_cash_adjustment(
        CashAdjustment(
            amount=Decimal("100"),
            reason="Topping up change",
            created_at=datetime(2026, 8, 15, 9, 30, 0),
        )
    )
    db._conn.execute(
        "CREATE TRIGGER sabotage_adjustments BEFORE INSERT ON cash_adjustments"
        " BEGIN SELECT RAISE(ABORT, 'sabotaged'); END;"
    )
    db._conn.commit()
    with pytest.raises(PersistenceError):
        db.save_cash_adjustment(
            CashAdjustment(
                amount=Decimal("-50"),
                reason="Removing change",
                created_at=datetime(2026, 8, 15, 10, 0, 0),
            )
        )
    adjustments = db.get_cash_adjustments()
    assert len(adjustments) == 1
    assert adjustments[0].amount == Decimal("100")
    assert adjustments[0].reason == "Topping up change"


# -- sequence and wipe contracts --------------------------------------------


def test_sequence_gaps_are_tolerated(adapter):
    db = adapter()
    db.save_sale(_sale(1, 2))
    db.save_sale(_sale(5, 1))
    sales = db.get_sales()
    assert [s.seq for s in sales] == [1, 5]


def test_wipe_clears_records_and_keeps_schema(adapter):
    db = adapter()
    db.save_settings(
        Settings(
            device_name="Till A",
            float_amount=Decimal("500"),
            catalog=[
                Item(item_id="MUG", name="Mug", price=Decimal("60"))
            ],
        )
    )
    db.save_sale(_sale(1, 2))
    db.save_cash_adjustment(
        CashAdjustment(
            amount=Decimal("100"),
            reason="Topping up change",
            created_at=datetime(2026, 8, 15, 9, 30, 0),
        )
    )
    version_before = db._conn.execute("PRAGMA user_version").fetchone()[0]

    db.wipe()

    assert db._conn.execute("PRAGMA user_version").fetchone()[0] == version_before
    tables = {
        row["name"]
        for row in db._conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    assert {"settings", "catalog", "sales", "cash_adjustments"} <= tables
    assert db.load_settings() is None
    assert db.get_sales() == []
    assert db.get_cash_adjustments() == []
