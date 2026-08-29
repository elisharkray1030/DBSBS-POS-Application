"""Schema and migrations for the device database (CONTEXT.md: Device database).

The schema owner: the DDL for every table, plus a versioned migration ladder
that brings an older device database up to the current schema. The adapter
applies it at open. This module knows nothing of the domain types and owns no
record conversion; it works only on a raw connection.
"""

from __future__ import annotations

import sqlite3

# The current schema version. Bump when the ladder gains a step.
LATEST_VERSION = 2

_SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS catalog (
    item_id           TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    price             TEXT NOT NULL,
    starting_quantity INTEGER,
    sold_out          INTEGER NOT NULL DEFAULT 0,
    source_cells      TEXT
);
CREATE TABLE IF NOT EXISTS sales (
    seq         INTEGER PRIMARY KEY,
    status      TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    device_name TEXT NOT NULL,
    line_items  TEXT NOT NULL,
    tenders     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cash_adjustments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    amount     TEXT NOT NULL,
    reason     TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def create_tables(conn: sqlite3.Connection) -> None:
    """Create the tables if they do not already exist."""
    conn.executescript(_SCHEMA)


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create the tables and bring the database up to the current schema.

    A freshly created database is built at the latest schema directly and
    stamped to the latest version. An existing database is walked up the
    migration ladder from its recorded version. Version 0 is treated as
    "legacy" — older code never stamped a version — so migration 1 stays
    tolerant of all the shapes that shipped before versioning.
    """
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    conn.executescript(_SCHEMA)
    if not tables:
        conn.execute(f"PRAGMA user_version = {LATEST_VERSION}")
        return
    migrate(conn)


def migrate(conn: sqlite3.Connection) -> None:
    """Walk the versioned migration ladder from the recorded version."""
    version = _user_version(conn)
    if version < 1:
        _migrate_to_v1(conn)
    if version < 2:
        _migrate_to_v2(conn)
    if version < LATEST_VERSION:
        _set_version(conn, LATEST_VERSION)


def _user_version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def _set_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute(f"PRAGMA user_version = {version}")


def _migrate_to_v1(conn: sqlite3.Connection) -> None:
    """Own source-cell preservation for databases that predate it.

    Adds the source_cells column for databases written before the Stock sheet
    module owned source-cell preservation, backfills it from the legacy
    raw_cells column when present, and drops that legacy column. Tolerant of
    databases already at this shape (older code never stamped a version).
    """
    columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(catalog)")
    }
    if "source_cells" not in columns:
        conn.execute("ALTER TABLE catalog ADD COLUMN source_cells TEXT")
        if "raw_cells" in columns:
            conn.execute(
                "UPDATE catalog SET source_cells = raw_cells"
                " WHERE source_cells IS NULL AND raw_cells IS NOT NULL"
            )
    if "raw_cells" in columns:
        conn.execute("ALTER TABLE catalog DROP COLUMN raw_cells")


def _migrate_to_v2(conn: sqlite3.Connection) -> None:
    """A sale's durable record is its line items and tenders (ADR-0004).

    Drops the summary columns (total, cash, octopus, voucher) that databases
    created by older code stored beside the JSON; the figures are derived on
    read. Tolerant of databases already at this shape.
    """
    columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(sales)")
    }
    for column in ("total", "cash", "octopus", "voucher"):
        if column in columns:
            conn.execute(f"ALTER TABLE sales DROP COLUMN {column}")
