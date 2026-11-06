"""Switching the active Stock sheet retains sales and report history."""

from __future__ import annotations

import csv
from decimal import Decimal

import pytest

from pos.domain import (
    CASH,
    CatalogError,
    PersistenceError,
    PosError,
    SetupError,
    Tender,
)
from pos.facade import PosSession
from pos.persistence import InMemoryPersistence


def _write_sheet(path, *rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ItemID", "ItemName", "Price", "Inventory", "Sales", "Revenue"])
        writer.writerows([*row, "0", "0"] for row in rows)
    return path


def _read_rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.reader(handle))


def test_switch_keeps_historical_prices_and_uses_active_report_source(
    session, tmp_path
):
    first = _write_sheet(
        tmp_path / "first.csv",
        ["MUG", "Old mug", "60", "20"],
        ["OLD", "Removed item", "5", "10"],
    )
    second = _write_sheet(
        tmp_path / "second.csv",
        ["BDG", "Badge", "18", "40"],
        ["MUG", "  Active mug  ", "75.00", "010"],
    )
    session.set_device_name("Till A")
    session.set_float(500)
    session.load_catalog(first)

    session.add_item_to_sale("MUG", 2)
    session.add_item_to_sale("OLD", 1)
    session.settle_current_sale(
        [Tender(CASH, Decimal("125"), tendered=Decimal("125"))]
    )
    assert session.load_catalog(second) == 2
    assert session.stock_sheet_filename() == "second.csv"

    session.add_item_to_sale("MUG", 1)
    session.settle_current_sale(
        [Tender(CASH, Decimal("75"), tendered=Decimal("75"))]
    )

    sales = session.list_sales()
    assert [line.price for line in sales[0].line_items] == [
        Decimal("60"),
        Decimal("5"),
    ]
    assert sales[0].total == Decimal("125")
    assert sales[1].line_items[0].price == Decimal("75.00")
    assert session.running_summary().takings == Decimal("200")

    figures = session.end_of_day()
    assert [(row.item_id, row.count) for row in figures.sold_rows] == [
        ("MUG", 3),
        ("OLD", 1),
    ]

    report = [path for path in session.export_csv(tmp_path) if path.name.startswith("stocks-")]
    rows = _read_rows(report[0])
    assert rows[1:] == [
        ["BDG", "Badge", "18", "40", "0", "0"],
        ["MUG", "  Active mug  ", "75.00", "010", "3", "195.00"],
    ]


def test_switch_uses_incoming_inventory_minus_shared_event_sales_and_clears_sold_out(
    configured_session, tmp_path
):
    first = _write_sheet(tmp_path / "first.csv", ["MUG", "Mug", "60", "20"])
    second = _write_sheet(tmp_path / "second.csv", ["MUG", "Mug", "75", "22"])
    configured_session.load_catalog(first)
    configured_session.add_item_to_sale("MUG", 3)
    configured_session.settle_current_sale(
        [Tender(CASH, Decimal("180"), tendered=Decimal("180"))]
    )
    configured_session.mark_sold_out("MUG")

    configured_session.load_catalog(second)

    stock = configured_session.list_items()[0]
    assert stock.starting_quantity == 22
    assert stock.remaining == 19
    assert stock.sold_out is False


def test_switch_clamps_negative_remaining_to_zero_and_keeps_sold_out(
    configured_session, tmp_path
):
    first = _write_sheet(tmp_path / "first.csv", ["MUG", "Mug", "60", "20"])
    second = _write_sheet(tmp_path / "second.csv", ["MUG", "Mug", "75", "2"])
    configured_session.load_catalog(first)
    configured_session.add_item_to_sale("MUG", 3)
    configured_session.settle_current_sale(
        [Tender(CASH, Decimal("180"), tendered=Decimal("180"))]
    )

    configured_session.load_catalog(second)

    stock = configured_session.list_items()[0]
    assert stock.remaining == 0
    assert stock.sold_out is False


def test_manual_catalog_edits_apply_to_future_sales_and_exported_source_values(
    configured_session, tmp_path
):
    source = _write_sheet(
        tmp_path / "active.csv", [" MUG ", "Mug", "60", "20"]
    )
    configured_session.load_catalog(source)
    configured_session.add_item_to_sale("MUG", 1)
    configured_session.settle_current_sale(
        [Tender(CASH, Decimal("60"), tendered=Decimal("60"))]
    )
    configured_session.mark_sold_out("MUG")

    configured_session.edit_catalog_item(
        "MUG", name="Mug updated", price="70", starting_quantity=22
    )
    stock = configured_session.list_items()[0]
    assert (stock.name, stock.price, stock.starting_quantity, stock.remaining) == (
        "Mug updated", Decimal("70"), 22, 21
    )
    assert stock.sold_out is False
    assert configured_session.get_sale(1).line_items[0].price == Decimal("60")

    report = [
        path
        for path in configured_session.export_csv(tmp_path)
        if path.name.startswith("stocks-")
    ]
    assert _read_rows(report[0])[1] == [
        " MUG ", "Mug updated", "70", "22", "1", "60"
    ]
    # Editing the active catalog must not mutate the selected source file.
    assert _read_rows(source)[1] == [" MUG ", "Mug", "60", "20", "0", "0"]


def test_catalog_edit_requires_empty_current_sale_and_invalidates_export(
    configured_session, tmp_path
):
    configured_session.export_csv(tmp_path)
    configured_session.add_item_to_sale("MUG", 1)
    with pytest.raises(SetupError, match="Settle the current sale"):
        configured_session.edit_catalog_item(
            "MUG", name="Mug", price="70", starting_quantity=20
        )
    configured_session.begin_sale()
    configured_session.edit_catalog_item(
        "MUG", name="Mug", price="70", starting_quantity=20
    )
    with pytest.raises(PosError, match="Wipe blocked"):
        configured_session.wipe()


def test_catalog_edit_validation_and_persistence_failure_are_atomic(
    clock, tmp_path
):
    store = _FailingSettingsStore()
    session = PosSession(store, clock=clock)
    sheet = _write_sheet(tmp_path / "source.csv", ["MUG", "Mug", "60", "20"])
    session.set_device_name("Till A")
    session.set_float(500)
    session.load_catalog(sheet)
    session.export_csv(tmp_path)
    with pytest.raises(SetupError, match="cannot be empty"):
        session.edit_catalog_item(
            "MUG", name="  ", price="70", starting_quantity=20
        )
    with pytest.raises(SetupError, match="Starting quantity must be a whole number"):
        session.edit_catalog_item(
            "MUG", name="Mug", price="70", starting_quantity="not a number"
        )
    with pytest.raises(SetupError, match="Starting quantity cannot be negative"):
        session.edit_catalog_item(
            "MUG", name="Mug", price="70", starting_quantity=-1
        )
    store.fail_saves = True
    with pytest.raises(PersistenceError):
        session.edit_catalog_item(
            "MUG", name="New name", price="70", starting_quantity=20
        )
    assert session.list_items()[0].name == "Mug"
    session.wipe()  # failed edit did not invalidate the prior export


def test_invalid_sheet_leaves_active_catalog_and_sales_unchanged(
    session, tmp_path
):
    original = _write_sheet(
        tmp_path / "original.csv", ["MUG", "  Mug  ", "60.00", "020"]
    )
    session.set_device_name("Till A")
    session.set_float(500)
    session.load_catalog(original)
    session.add_item_to_sale("MUG", 1)
    session.settle_current_sale(
        [Tender(CASH, Decimal("60"), tendered=Decimal("60"))]
    )
    bad = tmp_path / "bad.csv"
    bad.write_text("wrong,header\n", encoding="utf-8")

    with pytest.raises(CatalogError):
        session.load_catalog(bad)

    assert session.stock_sheet_filename() == "original.csv"
    assert [(item.item_id, item.price) for item in session.list_items()] == [
        ("MUG", Decimal("60"))
    ]
    assert session.get_sale(1).line_items[0].price == Decimal("60")
    report = [path for path in session.export_csv(tmp_path) if path.name.startswith("stocks-")]
    assert _read_rows(report[0])[1] == [
        "MUG",
        "  Mug  ",
        "60.00",
        "020",
        "1",
        "60.00",
    ]


def test_cannot_change_sheet_while_current_sale_has_items(session, tmp_path):
    first = _write_sheet(tmp_path / "first.csv", ["MUG", "Mug", "60", "20"])
    session.load_catalog(first)
    session.add_item_to_sale("MUG", 1)

    with pytest.raises(SetupError, match="Settle the current sale or remove all items"):
        session.load_catalog(tmp_path / "does-not-exist.csv")

    assert session.stock_sheet_filename() == "first.csv"
    assert session.current_sale_items()[0].price == Decimal("60")


class _FailingSettingsStore(InMemoryPersistence):
    def __init__(self):
        super().__init__()
        self.fail_saves = False

    def save_settings(self, settings):
        if self.fail_saves:
            raise PersistenceError("sabotaged settings write")
        super().save_settings(settings)


def test_failed_sheet_persistence_keeps_catalog_filename_and_export_state(
    clock, tmp_path
):
    store = _FailingSettingsStore()
    session = PosSession(store, clock=clock)
    first = _write_sheet(tmp_path / "first.csv", ["MUG", "Mug", "60", "20"])
    second = _write_sheet(tmp_path / "second.csv", ["MUG", "Mug", "75", "10"])
    session.set_device_name("Till A")
    session.set_float(500)
    session.load_catalog(first)
    session.add_item_to_sale("MUG", 1)
    session.settle_current_sale(
        [Tender(CASH, Decimal("60"), tendered=Decimal("60"))]
    )
    session.export_csv(tmp_path)
    store.fail_saves = True

    with pytest.raises(PersistenceError):
        session.load_catalog(second)

    assert session.stock_sheet_filename() == "first.csv"
    assert session.list_items()[0].price == Decimal("60")
    assert session.get_sale(1).total == Decimal("60")
    # The failed switch did not invalidate the successfully recorded export.
    session.wipe()
    assert session.is_configured() is False


def test_switch_after_export_requires_a_fresh_export_before_wipe(
    configured_session, tmp_path
):
    configured_session.add_item_to_sale("MUG", 1)
    configured_session.settle_current_sale(
        [Tender(CASH, Decimal("60"), tendered=Decimal("60"))]
    )
    configured_session.export_csv(tmp_path)
    replacement = _write_sheet(
        tmp_path / "replacement.csv", ["MUG", "Mug", "65", "20"]
    )

    configured_session.load_catalog(replacement)
    with pytest.raises(PosError, match="Wipe blocked"):
        configured_session.wipe()

    configured_session.export_csv(tmp_path)
    configured_session.wipe()
    assert configured_session.is_configured() is False


def test_switch_after_export_without_sales_still_requires_fresh_export(
    configured_session, tmp_path
):
    configured_session.export_csv(tmp_path)
    replacement = _write_sheet(
        tmp_path / "replacement.csv", ["MUG", "Mug", "65", "20"]
    )
    configured_session.load_catalog(replacement)

    with pytest.raises(PosError, match="Wipe blocked"):
        configured_session.wipe()

    configured_session.export_csv(tmp_path)
    configured_session.wipe()
    assert configured_session.is_configured() is False
