"""SQLite-backed persistence for the production app.

One file per device. Every mutation is committed in its own transaction so a
completed sale is on disk the instant it is made (survives a crash).

The adapter owns the connection and the transactions; the schema and migration
live in the schema owner and the durable-record conversion in the conversion
owner (architecture umbrella U3).
"""

from __future__ import annotations

import sqlite3
from functools import wraps
from pathlib import Path

from . import sqlite_records, sqlite_schema
from .domain import CashAdjustment, PersistenceError, Sale, Settings

_STORE = "device database"


def _guard(fn):
    """Translate raw database errors into domain errors.

    Corruption errors pass through untouched: they are raised by the record
    conversion, not by the database.
    """

    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        try:
            return fn(self, *args, **kwargs)
        except sqlite3.Error as exc:
            raise PersistenceError(f"{_STORE} {fn.__name__}: {exc}") from exc

    return wrapper


class SqlitePersistence:
    def __init__(self, db_path: str | Path) -> None:
        try:
            self._conn = sqlite3.connect(str(db_path))
            self._conn.row_factory = sqlite3.Row
            sqlite_schema.ensure_schema(self._conn)
            self._conn.commit()
        except sqlite3.Error as exc:
            raise PersistenceError(
                f"Could not open the {_STORE}: {exc}"
            ) from exc

    def close(self) -> None:
        self._conn.close()

    # -- settings / catalog -------------------------------------------------

    @_guard
    def load_settings(self) -> Settings | None:
        settings = Settings()
        found = False
        for row in self._conn.execute("SELECT key, value FROM settings"):
            if row["key"] == "device_name":
                if row["value"]:
                    settings.device_name = sqlite_records.parse_device_name(
                        row["value"], "Settings (device_name)"
                    )
                found = True
            elif row["key"] == "float":
                settings.float_amount = sqlite_records.parse_float(
                    row["value"], "Settings (float)"
                )
                found = True
            elif row["key"] == "last_export_at" and row["value"]:
                settings.last_export_at = sqlite_records.parse_dt(
                    row["value"], "Settings (last_export_at)"
                )
                found = True
        rows = self._conn.execute(
            "SELECT item_id, name, price, starting_quantity, sold_out,"
            " source_cells FROM catalog"
        ).fetchall()
        if not rows and not found:
            return None
        settings.catalog = [sqlite_records.item_from_row(row) for row in rows]
        settings.source_cells = {
            row["item_id"]: sqlite_records.source_cells_from_row(row)
            for row in rows
            if row["source_cells"] is not None
        }
        return settings

    @_guard
    def save_settings(self, settings: Settings) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                ("device_name", settings.device_name),
            )
            float_value = (
                str(settings.float_amount)
                if settings.float_amount is not None
                else ""
            )
            self._conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                ("float", float_value),
            )
            export_value = (
                sqlite_records.iso(settings.last_export_at)
                if settings.last_export_at is not None
                else ""
            )
            self._conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                ("last_export_at", export_value),
            )
            self._conn.execute("DELETE FROM catalog")
            self._conn.executemany(
                "INSERT INTO catalog (item_id, name, price, starting_quantity,"
                " sold_out, source_cells)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                [
                    sqlite_records.catalog_row_values(
                        item, settings.source_cells_for(item.item_id)
                    )
                    for item in settings.catalog
                ],
            )

    # -- sales --------------------------------------------------------------

    @_guard
    def next_sale_sequence(self) -> int:
        row = self._conn.execute("SELECT MAX(seq) AS max_seq FROM sales").fetchone()
        return (row["max_seq"] if row["max_seq"] is not None else 0) + 1

    @_guard
    def save_sale(self, sale: Sale) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO sales"
                " (seq, status, created_at, updated_at, device_name,"
                "  line_items, tenders)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                sqlite_records.sale_to_row(sale),
            )

    @_guard
    def get_sales(self) -> list[Sale]:
        rows = self._conn.execute("SELECT * FROM sales ORDER BY seq").fetchall()
        return [sqlite_records.sale_from_row(row) for row in rows]

    # -- cash adjustments ---------------------------------------------------

    @_guard
    def save_cash_adjustment(self, adjustment: CashAdjustment) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT INTO cash_adjustments (amount, reason, created_at)"
                " VALUES (?, ?, ?)",
                (
                    str(adjustment.amount),
                    adjustment.reason,
                    sqlite_records.iso(adjustment.created_at),
                ),
            )

    @_guard
    def get_cash_adjustments(self) -> list[CashAdjustment]:
        rows = self._conn.execute(
            "SELECT amount, reason, created_at FROM cash_adjustments ORDER BY id"
        ).fetchall()
        return [sqlite_records.adjustment_from_row(row) for row in rows]

    # -- wipe ---------------------------------------------------------------

    @_guard
    def wipe(self) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM settings")
            self._conn.execute("DELETE FROM catalog")
            self._conn.execute("DELETE FROM sales")
            self._conn.execute("DELETE FROM cash_adjustments")
