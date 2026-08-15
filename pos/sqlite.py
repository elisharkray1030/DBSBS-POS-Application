"""SQLite-backed persistence for the production app.

One file per device. Every mutation is committed in its own transaction so a
completed sale is on disk the instant it is made (survives a crash).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from .domain import (
    CashAdjustment,
    Item,
    LineItem,
    Sale,
    Settings,
    Tender,
    money,
)

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
    raw_cells         TEXT
);
CREATE TABLE IF NOT EXISTS sales (
    seq         INTEGER PRIMARY KEY,
    status      TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    device_name TEXT NOT NULL,
    total       TEXT NOT NULL,
    cash        TEXT NOT NULL,
    octopus     TEXT NOT NULL,
    voucher     TEXT NOT NULL,
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


def _iso(value: datetime) -> str:
    return value.isoformat()


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _line_item_to_dict(line: LineItem) -> dict:
    return {
        "item_id": line.item_id,
        "item_name": line.item_name,
        "quantity": line.quantity,
        "price": str(line.price),
    }


def _line_item_from_dict(data: dict) -> LineItem:
    return LineItem(
        item_id=data.get("item_id", ""),
        item_name=data["item_name"],
        quantity=int(data["quantity"]),
        price=money(data["price"]),
    )


def _tender_to_dict(tender: Tender) -> dict:
    return {
        "method": tender.method,
        "amount": str(tender.amount),
        "tendered": str(tender.tendered) if tender.tendered is not None else None,
    }


def _tender_from_dict(data: dict) -> Tender:
    tendered = money(data["tendered"]) if data.get("tendered") is not None else None
    return Tender(
        method=data["method"],
        amount=money(data["amount"]),
        tendered=tendered,
    )


class SqlitePersistence:
    def __init__(self, db_path: str | Path) -> None:
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._migrate()
        self._conn.commit()

    def _migrate(self) -> None:
        """Bring pre-raw_cells device databases up to the current schema."""
        columns = {
            row["name"] for row in self._conn.execute("PRAGMA table_info(catalog)")
        }
        if "raw_cells" not in columns:
            self._conn.execute("ALTER TABLE catalog ADD COLUMN raw_cells TEXT")

    def close(self) -> None:
        self._conn.close()

    # -- settings / catalog -------------------------------------------------

    def load_settings(self) -> Settings | None:
        settings = Settings()
        found = False
        for row in self._conn.execute("SELECT key, value FROM settings"):
            if row["key"] == "device_name":
                settings.device_name = row["value"]
                found = True
            elif row["key"] == "float":
                settings.float_amount = money(row["value"])
                found = True
            elif row["key"] == "last_export_at" and row["value"]:
                settings.last_export_at = _parse_dt(row["value"])
                found = True
        rows = self._conn.execute(
            "SELECT item_id, name, price, starting_quantity, sold_out, raw_cells"
            " FROM catalog"
        ).fetchall()
        if not rows and not found:
            return None
        settings.catalog = [
            Item(
                item_id=row["item_id"],
                name=row["name"],
                price=money(row["price"]),
                starting_quantity=row["starting_quantity"],
                sold_out=bool(row["sold_out"]),
                raw_cells=(
                    tuple(json.loads(row["raw_cells"]))
                    if row["raw_cells"] is not None
                    else None
                ),
            )
            for row in rows
        ]
        return settings

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
                _iso(settings.last_export_at)
                if settings.last_export_at is not None
                else ""
            )
            self._conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                ("last_export_at", export_value),
            )
            self._conn.execute("DELETE FROM catalog")
            self._conn.executemany(
                "INSERT INTO catalog (item_id, name, price, starting_quantity, sold_out, raw_cells)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        item.item_id,
                        item.name,
                        str(item.price),
                        item.starting_quantity,
                        1 if item.sold_out else 0,
                        json.dumps(list(item.raw_cells))
                        if item.raw_cells is not None
                        else None,
                    )
                    for item in settings.catalog
                ],
            )

    # -- sales --------------------------------------------------------------

    def next_sale_sequence(self) -> int:
        row = self._conn.execute("SELECT MAX(seq) AS max_seq FROM sales").fetchone()
        return (row["max_seq"] if row["max_seq"] is not None else 0) + 1

    def save_sale(self, sale: Sale) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO sales"
                " (seq, status, created_at, updated_at, device_name, total,"
                "  cash, octopus, voucher, line_items, tenders)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    sale.seq,
                    sale.status,
                    _iso(sale.created_at),
                    _iso(sale.updated_at),
                    sale.device_name,
                    str(sale.total),
                    str(sale.tender_sum("cash")),
                    str(sale.tender_sum("octopus")),
                    str(sale.tender_sum("voucher")),
                    json.dumps([_line_item_to_dict(l) for l in sale.line_items]),
                    json.dumps([_tender_to_dict(t) for t in sale.tenders]),
                ),
            )

    def get_sales(self) -> list[Sale]:
        rows = self._conn.execute("SELECT * FROM sales ORDER BY seq").fetchall()
        return [self._sale_from_row(row) for row in rows]

    @staticmethod
    def _sale_from_row(row: sqlite3.Row) -> Sale:
        line_items = [
            _line_item_from_dict(data)
            for data in json.loads(row["line_items"])
        ]
        tenders = [
            _tender_from_dict(data) for data in json.loads(row["tenders"])
        ]
        return Sale(
            seq=int(row["seq"]),
            created_at=_parse_dt(row["created_at"]),
            updated_at=_parse_dt(row["updated_at"]),
            status=row["status"],
            line_items=line_items,
            tenders=tenders,
            device_name=row["device_name"],
        )

    # -- cash adjustments ---------------------------------------------------

    def save_cash_adjustment(self, adjustment: CashAdjustment) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT INTO cash_adjustments (amount, reason, created_at)"
                " VALUES (?, ?, ?)",
                (str(adjustment.amount), adjustment.reason, _iso(adjustment.created_at)),
            )

    def get_cash_adjustments(self) -> list[CashAdjustment]:
        rows = self._conn.execute(
            "SELECT amount, reason, created_at FROM cash_adjustments ORDER BY id"
        ).fetchall()
        return [
            CashAdjustment(
                amount=money(row["amount"]),
                reason=row["reason"],
                created_at=_parse_dt(row["created_at"]),
            )
            for row in rows
        ]

    # -- wipe ---------------------------------------------------------------

    def wipe(self) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM settings")
            self._conn.execute("DELETE FROM catalog")
            self._conn.execute("DELETE FROM sales")
            self._conn.execute("DELETE FROM cash_adjustments")
