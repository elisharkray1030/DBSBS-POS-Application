"""Stock sheet catalog load (ticket 01) and read-only catalog (ticket 02).

The organizer's Stock sheet CSV (columns `ItemID, ItemName, Price, Inventory,
Sales, Revenue`) is the only accepted catalog input. Each item's identity is
its Item ID. The catalog is read-only once loaded: no in-app add or price fix.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from pos.domain import CatalogError


def test_inventory_column_sets_starting_quantity(session, catalog_file):
    session.load_catalog(catalog_file)
    by_id = {i.item_id: i for i in session.list_items()}
    assert by_id["MUG"].starting_quantity == 20
    assert by_id["BDG"].starting_quantity == 50
    assert by_id["PLUSH"].starting_quantity is None  # blank = sell-by-demand


def test_prefilled_sales_and_revenue_are_ignored(session, tmp_path):
    sheet = tmp_path / "stock.csv"
    sheet.write_text(
        "ItemID,ItemName,Price,Inventory,Sales,Revenue\n"
        "MUG,Mug,60,20,not-a-number,also-garbage\n",
        encoding="utf-8",
    )
    count = session.load_catalog(sheet)
    assert count == 1
    item = session.list_items()[0]
    assert item.item_id == "MUG"
    assert item.price == Decimal("60")
    assert item.starting_quantity == 20


def test_item_list_reports_item_id_alongside_name_and_price(session, catalog_file):
    session.load_catalog(catalog_file)
    mug = next(i for i in session.list_items() if i.item_id == "MUG")
    assert mug.item_id == "MUG"
    assert mug.name == "Mug"
    assert mug.price == Decimal("60")
    assert mug.starting_quantity == 20


def test_old_name_price_quantity_header_is_rejected(session, tmp_path):
    old = tmp_path / "old.csv"
    old.write_text("Name, Price, Quantity\nMug, 60, 20\n", encoding="utf-8")
    with pytest.raises(CatalogError):
        session.load_catalog(old)


def test_missing_stock_sheet_is_rejected(session, tmp_path):
    with pytest.raises(CatalogError):
        session.load_catalog(tmp_path / "does-not-exist.csv")


def test_wrong_header_is_rejected(session, tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("ItemID, ItemName\nMUG, Mug\n", encoding="utf-8")
    with pytest.raises(CatalogError):
        session.load_catalog(bad)


def test_empty_stock_sheet_is_rejected(session, tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(CatalogError):
        session.load_catalog(empty)


def test_missing_item_id_is_rejected(session, tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text(
        "ItemID,ItemName,Price,Inventory,Sales,Revenue\n"
        ",Mug,60,20,0,0\n",
        encoding="utf-8",
    )
    with pytest.raises(CatalogError):
        session.load_catalog(bad)


def test_duplicate_item_id_is_rejected(session, tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text(
        "ItemID,ItemName,Price,Inventory,Sales,Revenue\n"
        "MUG,Mug,60,20,0,0\n"
        "MUG,Second Mug,60,10,0,0\n",
        encoding="utf-8",
    )
    with pytest.raises(CatalogError):
        session.load_catalog(bad)


def test_non_numeric_price_is_rejected(session, tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text(
        "ItemID,ItemName,Price,Inventory,Sales,Revenue\n"
        "MUG,Mug,sixty,20,0,0\n",
        encoding="utf-8",
    )
    with pytest.raises(CatalogError):
        session.load_catalog(bad)


def test_catalog_with_item_ids_survives_reopen(clock, catalog_file):
    from pos.facade import PosSession
    from pos.persistence import InMemoryPersistence

    store = InMemoryPersistence()
    first = PosSession(store, clock=clock)
    first.load_catalog(catalog_file)

    reopened = PosSession(store, clock=clock)
    items = reopened.list_items()
    assert [i.item_id for i in items] == ["MUG", "BDG", "PLUSH"]


# -- ticket 02: read-only catalog -----------------------------------------


def test_add_item_and_fix_price_are_removed_from_the_facade(session):
    assert not hasattr(session, "add_catalog_item")
    assert not hasattr(session, "fix_item_price")
