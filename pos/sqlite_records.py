"""Durable-record conversion for the device database (CONTEXT.md: Device database).

The conversion owner: domain records to and from the stored rows of the device
database. It knows the JSON shapes and text encodings of stored values; it does
not know the schema version or how to run SQL. The adapter keeps the SQL, the
connection, and the transaction-per-write discipline.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from decimal import Decimal

from .domain import (
    CASH,
    COMPLETED,
    OCTOPUS,
    VOIDED,
    VOUCHER,
    CashAdjustment,
    CorruptRecordError,
    InvalidMoney,
    InvalidSettlement,
    Item,
    LineItem,
    Money,
    Sale,
    SourceCells,
    Tender,
    money,
    validate_settlement,
)


def iso(value: datetime) -> str:
    return value.isoformat()


def _require_text(value, where: str, what: str) -> str:
    if not isinstance(value, str) or not value:
        raise CorruptRecordError(f"{where}: corrupt {what} {value!r}")
    return value


def _require_int(value, where: str, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CorruptRecordError(f"{where}: corrupt {what} {value!r}")
    return value


def parse_dt(value: str, where: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise CorruptRecordError(f"{where}: bad timestamp {value!r}") from exc


def parse_money(value: str, where: str):
    try:
        return money(value)
    except InvalidMoney as exc:
        raise CorruptRecordError(f"{where}: bad money value {value!r}") from exc


def parse_float(value: str, where: str) -> Money | None:
    """The stored Float: empty reads as unset, otherwise finite nonnegative."""
    if not value:
        return None
    parsed = parse_money(value, where)
    if parsed < 0:
        raise CorruptRecordError(f"{where}: negative float {value!r}")
    return parsed


def parse_device_name(value: str, where: str) -> str:
    """A stored settings device name must be usable non-empty text.

    An empty stored value represents a setup that never named the device; a
    present-but-empty (whitespace-only) value is corruption.
    """
    if not isinstance(value, str) or not value.strip():
        raise CorruptRecordError(f"{where}: corrupt device name {value!r}")
    return value


def _require_whole_quantity(value, where: str) -> int:
    """A stored sale-line quantity must be a strict whole number.

    `int()` is never used on the stored value: a fractional or non-integer
    JSON number would otherwise be silently truncated or coerced.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise CorruptRecordError(f"{where}: corrupt quantity {value!r}")
    if value < 1:
        raise CorruptRecordError(f"{where}: corrupt quantity {value!r}")
    return value


def line_item_to_dict(line: LineItem) -> dict:
    return {
        "item_id": line.item_id,
        "item_name": line.item_name,
        "quantity": line.quantity,
        "price": str(line.price),
    }


def line_item_from_dict(data: dict, where: str) -> LineItem:
    try:
        item_id = data["item_id"]
        item_name = data["item_name"]
        quantity = data["quantity"]
        price = parse_money(data["price"], where)
    except (KeyError, TypeError, ValueError) as exc:
        raise CorruptRecordError(f"{where}: corrupt line item ({exc})") from exc
    item_id = _require_text(item_id, where, "item id")
    item_name = _require_text(item_name, where, "item name")
    quantity = _require_whole_quantity(quantity, where)
    if price < 0:
        raise CorruptRecordError(f"{where}: negative line price {price!r}")
    return LineItem(item_id=item_id, item_name=item_name, quantity=quantity, price=price)


def tender_to_dict(tender: Tender) -> dict:
    return {
        "method": tender.method,
        "amount": str(tender.amount),
        "tendered": str(tender.tendered) if tender.tendered is not None else None,
    }


def tender_from_dict(data: dict, where: str) -> Tender:
    try:
        method = data["method"]
        amount = parse_money(data["amount"], where)
        tendered = (
            parse_money(data["tendered"], where)
            if data.get("tendered") is not None
            else None
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise CorruptRecordError(f"{where}: corrupt tender ({exc})") from exc
    if method not in (CASH, OCTOPUS, VOUCHER):
        raise CorruptRecordError(f"{where}: unknown tender method {method!r}")
    return Tender(method=method, amount=amount, tendered=tendered)


def sale_to_row(sale: Sale) -> tuple:
    """The stored values for a sale: its durable record (ADR-0004).

    Figures are derived on read from the JSON, never stored beside it.
    """
    return (
        sale.seq,
        sale.status,
        iso(sale.created_at),
        iso(sale.updated_at),
        sale.device_name,
        json.dumps([line_item_to_dict(l) for l in sale.line_items]),
        json.dumps([tender_to_dict(t) for t in sale.tenders]),
    )


def sale_from_row(row: sqlite3.Row) -> Sale:
    try:
        seq = int(row["seq"])
        where = f"Sale {seq}"
        status = row["status"]
        device_name = row["device_name"]
        line_items = [
            line_item_from_dict(data, where)
            for data in json.loads(row["line_items"])
        ]
        tenders = [
            tender_from_dict(data, where) for data in json.loads(row["tenders"])
        ]
        created_at = parse_dt(row["created_at"], where)
        updated_at = parse_dt(row["updated_at"], where)
    except CorruptRecordError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise CorruptRecordError(
            f"Sale {row['seq']!r}: corrupt record ({exc})"
        ) from exc
    if status not in (COMPLETED, VOIDED):
        raise CorruptRecordError(f"{where}: unknown sale status {status!r}")
    device_name = _require_text(device_name, where, "device name")
    total = sum((line.total for line in line_items), Decimal("0"))
    try:
        validate_settlement(tenders, total)
    except InvalidSettlement as exc:
        raise CorruptRecordError(f"{where}: invalid settlement ({exc})") from exc
    return Sale(
        seq=seq,
        created_at=created_at,
        updated_at=updated_at,
        status=status,
        line_items=line_items,
        tenders=tenders,
        device_name=device_name,
    )


def item_from_row(row: sqlite3.Row) -> Item:
    where = f"Item {row['item_id']!r}"
    item_id = _require_text(row["item_id"], where, "item id")
    name = _require_text(row["name"], where, "name")
    starting_quantity = row["starting_quantity"]
    if starting_quantity is not None:
        starting_quantity = _require_int(
            starting_quantity, where, "starting quantity"
        )
        if starting_quantity < 0:
            raise CorruptRecordError(
                f"{where}: negative starting quantity {starting_quantity!r}"
            )
    sold_out = _require_int(row["sold_out"], where, "sold-out flag")
    if sold_out not in (0, 1):
        raise CorruptRecordError(f"{where}: corrupt sold-out flag {sold_out!r}")
    price = parse_money(row["price"], where)
    if price < 0:
        raise CorruptRecordError(f"{where}: negative price {price!r}")
    return Item(
        item_id=item_id,
        name=name,
        price=price,
        starting_quantity=starting_quantity,
        sold_out=bool(sold_out),
    )


def source_cells_from_row(row: sqlite3.Row) -> SourceCells:
    where = f"Item {row['item_id']!r}"
    try:
        cells = json.loads(row["source_cells"])
    except (json.JSONDecodeError, TypeError) as exc:
        raise CorruptRecordError(f"{where}: corrupt source cells") from exc
    if (
        not isinstance(cells, list)
        or len(cells) != 4
        or not all(isinstance(cell, str) for cell in cells)
    ):
        raise CorruptRecordError(f"{where}: corrupt source cells {cells!r}")
    return tuple(cells)


def catalog_row_values(item: Item, cells: SourceCells | None) -> tuple:
    return (
        item.item_id,
        item.name,
        str(item.price),
        item.starting_quantity,
        1 if item.sold_out else 0,
        json.dumps(list(cells)) if cells is not None else None,
    )


def adjustment_from_row(row: sqlite3.Row) -> CashAdjustment:
    return CashAdjustment(
        amount=parse_money(row["amount"], "Cash adjustment"),
        reason=row["reason"],
        created_at=parse_dt(row["created_at"], "Cash adjustment"),
    )
