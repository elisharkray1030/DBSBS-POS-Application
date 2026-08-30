"""Isolated tests for the Stock sheet module (architecture umbrella U1).

The Stock sheet round-trip rule — load validation, source-cell preservation,
and report-row generation — lives behind one module. These tests drive it
directly through its public functions; the session facade remains the
round-trip seam covered elsewhere.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from pos import stock_sheet
from pos.domain import CatalogError, Item


def write_sheet(tmp_path, text: str):
    path = tmp_path / "stock.csv"
    path.write_text(text, encoding="utf-8")
    return path


GOOD_CSV = (
    "ItemID,ItemName,Price,Inventory,Sales,Revenue\n"
    "MUG,Mug,60,20,30,1800\n"
    "BDG,Badge,15,50,10,150\n"
    "PLUSH,Plush Bear,120,,5,600\n"
)


# -- load_catalog ----------------------------------------------------------


def test_load_parses_items_with_domain_facts(tmp_path):
    sheet = write_sheet(tmp_path, GOOD_CSV)
    loaded = stock_sheet.load_catalog(sheet)
    assert [i.item_id for i in loaded.items] == ["MUG", "BDG", "PLUSH"]
    assert [i.name for i in loaded.items] == ["Mug", "Badge", "Plush Bear"]
    assert loaded.items[0].price == Decimal("60")
    assert loaded.items[0].starting_quantity == 20
    assert loaded.items[2].starting_quantity is None  # blank = sell-by-demand
    assert all(isinstance(i, Item) for i in loaded.items)


def test_load_records_source_cells_verbatim(tmp_path):
    sheet = write_sheet(
        tmp_path,
        "ItemID,ItemName,Price,Inventory,Sales,Revenue\n"
        "MUG,  Mug  ,60.00,020,0,0\n",
    )
    loaded = stock_sheet.load_catalog(sheet)
    assert loaded.source_cells["MUG"] == ("MUG", "  Mug  ", "60.00", "020")


def test_load_rejects_wrong_header(tmp_path):
    sheet = write_sheet(tmp_path, "Name, Price, Quantity\nMug, 60, 20\n")
    with pytest.raises(CatalogError):
        stock_sheet.load_catalog(sheet)


def test_load_rejects_empty_file(tmp_path):
    sheet = write_sheet(tmp_path, "")
    with pytest.raises(CatalogError):
        stock_sheet.load_catalog(sheet)


def test_load_rejects_header_only_file(tmp_path):
    sheet = write_sheet(tmp_path, "ItemID,ItemName,Price,Inventory,Sales,Revenue\n")
    with pytest.raises(CatalogError):
        stock_sheet.load_catalog(sheet)


def test_load_rejects_missing_item_id(tmp_path):
    sheet = write_sheet(
        tmp_path,
        "ItemID,ItemName,Price,Inventory,Sales,Revenue\n"
        ",Mug,60,20,0,0\n",
    )
    with pytest.raises(CatalogError):
        stock_sheet.load_catalog(sheet)


def test_load_rejects_duplicate_item_id(tmp_path):
    sheet = write_sheet(
        tmp_path,
        "ItemID,ItemName,Price,Inventory,Sales,Revenue\n"
        "MUG,Mug,60,20,0,0\n"
        "MUG,Second Mug,60,10,0,0\n",
    )
    with pytest.raises(CatalogError):
        stock_sheet.load_catalog(sheet)


def test_load_rejects_missing_item_name(tmp_path):
    sheet = write_sheet(
        tmp_path,
        "ItemID,ItemName,Price,Inventory,Sales,Revenue\n"
        "MUG,,60,20,0,0\n",
    )
    with pytest.raises(CatalogError):
        stock_sheet.load_catalog(sheet)


def test_load_rejects_blank_item_name(tmp_path):
    sheet = write_sheet(
        tmp_path,
        "ItemID,ItemName,Price,Inventory,Sales,Revenue\n"
        "MUG,   ,60,20,0,0\n",
    )
    with pytest.raises(CatalogError):
        stock_sheet.load_catalog(sheet)


def test_load_rejects_non_numeric_price(tmp_path):
    sheet = write_sheet(
        tmp_path,
        "ItemID,ItemName,Price,Inventory,Sales,Revenue\n"
        "MUG,Mug,sixty,20,0,0\n",
    )
    with pytest.raises(CatalogError):
        stock_sheet.load_catalog(sheet)


def test_load_rejects_non_whole_inventory(tmp_path):
    sheet = write_sheet(
        tmp_path,
        "ItemID,ItemName,Price,Inventory,Sales,Revenue\n"
        "MUG,Mug,60,twenty,0,0\n",
    )
    with pytest.raises(CatalogError):
        stock_sheet.load_catalog(sheet)


def test_load_rejects_negative_inventory(tmp_path):
    sheet = write_sheet(
        tmp_path,
        "ItemID,ItemName,Price,Inventory,Sales,Revenue\n"
        "MUG,Mug,60,-1,0,0\n",
    )
    with pytest.raises(CatalogError):
        stock_sheet.load_catalog(sheet)


def test_load_ignores_prefilled_sales_and_revenue(tmp_path):
    sheet = write_sheet(
        tmp_path,
        "ItemID,ItemName,Price,Inventory,Sales,Revenue\n"
        "MUG,Mug,60,20,not-a-number,also-garbage\n",
    )
    loaded = stock_sheet.load_catalog(sheet)
    assert loaded.items[0].price == Decimal("60")
    assert loaded.items[0].starting_quantity == 20


def test_load_skips_entirely_blank_rows(tmp_path):
    sheet = write_sheet(
        tmp_path,
        "ItemID,ItemName,Price,Inventory,Sales,Revenue\n"
        "MUG,Mug,60,20,0,0\n"
        "\n",
    )
    loaded = stock_sheet.load_catalog(sheet)
    assert [i.item_id for i in loaded.items] == ["MUG"]


def test_load_missing_file_raises(tmp_path):
    with pytest.raises(CatalogError):
        stock_sheet.load_catalog(tmp_path / "does-not-exist.csv")


def test_load_rejects_negative_price(tmp_path):
    sheet = write_sheet(
        tmp_path,
        "ItemID,ItemName,Price,Inventory,Sales,Revenue\n"
        "MUG,Mug,-60,20,0,0\n",
    )
    with pytest.raises(CatalogError):
        stock_sheet.load_catalog(sheet)


def test_load_accepts_zero_price(tmp_path):
    sheet = write_sheet(
        tmp_path,
        "ItemID,ItemName,Price,Inventory,Sales,Revenue\n"
        "MUG,Mug,0,20,0,0\n",
    )
    loaded = stock_sheet.load_catalog(sheet)
    assert loaded.items[0].price == Decimal("0")


def test_load_rejects_non_finite_price(tmp_path):
    sheet = write_sheet(
        tmp_path,
        "ItemID,ItemName,Price,Inventory,Sales,Revenue\n"
        "MUG,Mug,NaN,20,0,0\n",
    )
    with pytest.raises(CatalogError):
        stock_sheet.load_catalog(sheet)


def test_load_rejects_row_wider_than_six_columns(tmp_path):
    sheet = write_sheet(
        tmp_path,
        "ItemID,ItemName,Price,Inventory,Sales,Revenue\n"
        "MUG,Mug,60,20,0,0,EXTRA\n",
    )
    with pytest.raises(CatalogError, match="MUG"):
        stock_sheet.load_catalog(sheet)


def test_load_rejects_trailing_empty_seventh_field(tmp_path):
    sheet = write_sheet(
        tmp_path,
        "ItemID,ItemName,Price,Inventory,Sales,Revenue\n"
        "MUG,Mug,60,20,0,0,\n",
    )
    with pytest.raises(CatalogError, match="MUG"):
        stock_sheet.load_catalog(sheet)


def test_load_short_row_error_names_the_row(tmp_path):
    sheet = write_sheet(
        tmp_path,
        "ItemID,ItemName,Price,Inventory,Sales,Revenue\n"
        "MUG,Mug,60,20,0,0\n"
        "BDG\n",
    )
    with pytest.raises(CatalogError, match="Row 3"):
        stock_sheet.load_catalog(sheet)


def test_load_invalid_encoding_raises_catalog_error(tmp_path):
    path = tmp_path / "bad-encoding.csv"
    path.write_bytes(
        b"ItemID,ItemName,Price,Inventory,Sales,Revenue\n"
        b"MUG,Mug,60,20,\xff,\xff\n"
    )
    with pytest.raises(CatalogError):
        stock_sheet.load_catalog(path)


def test_load_csv_parse_failure_raises_catalog_error(tmp_path):
    import csv as csv_module

    old_limit = csv_module.field_size_limit()
    try:
        csv_module.field_size_limit(10)
        sheet = write_sheet(
            tmp_path,
            "ItemID,ItemName,Price,Inventory,Sales,Revenue\n"
            "MUG," + "x" * 100 + ",60,20,0,0\n",
        )
        with pytest.raises(CatalogError):
            stock_sheet.load_catalog(sheet)
    finally:
        csv_module.field_size_limit(old_limit)


# -- build_report_rows -----------------------------------------------------


def test_report_rows_pass_source_cells_through_verbatim():
    items = [
        Item(item_id="MUG", name="Mug", price=Decimal("60"), starting_quantity=20),
        Item(item_id="BDG", name="Badge", price=Decimal("15"), starting_quantity=50),
    ]
    source_cells = {
        "MUG": ("MUG", "  Mug  ", "60.00", "020"),
        "BDG": ("BDG", "Badge", "15.0", "50"),
    }
    sold_by_item = {"MUG": (2, Decimal("120"))}
    rows = stock_sheet.build_report_rows(items, sold_by_item, source_cells)
    assert rows == [
        ["MUG", "  Mug  ", "60.00", "020", "2", "120"],
        ["BDG", "Badge", "15.0", "50", "0", "0"],
    ]


def test_report_rows_synthesize_fallback_from_domain_fields():
    items = [
        Item(item_id="MUG", name="Mug", price=Decimal("60"), starting_quantity=20),
        Item(
            item_id="PLUSH",
            name="Plush Bear",
            price=Decimal("120"),
            starting_quantity=None,
        ),
    ]
    rows = stock_sheet.build_report_rows(items, {}, {})
    assert rows == [
        ["MUG", "Mug", "60", "20", "0", "0"],
        ["PLUSH", "Plush Bear", "120", "", "0", "0"],
    ]


def test_report_rows_follow_catalog_order_and_fill_sales_revenue():
    items = [
        Item(item_id="MUG", name="Mug", price=Decimal("60"), starting_quantity=20),
        Item(item_id="BDG", name="Badge", price=Decimal("15"), starting_quantity=50),
        Item(item_id="PLUSH", name="Plush Bear", price=Decimal("120")),
    ]
    source_cells = {
        "MUG": ("MUG", "Mug", "60", "20"),
        "BDG": ("BDG", "Badge", "15", "50"),
        "PLUSH": ("PLUSH", "Plush Bear", "120", ""),
    }
    sold_by_item = {"BDG": (3, Decimal("45")), "MUG": (2, Decimal("120"))}
    rows = stock_sheet.build_report_rows(items, sold_by_item, source_cells)
    assert [r[0] for r in rows] == ["MUG", "BDG", "PLUSH"]
    assert rows[0][4:] == ["2", "120"]
    assert rows[1][4:] == ["3", "45"]
    assert rows[2][4:] == ["0", "0"]


def test_stock_sheet_header_is_exported():
    assert stock_sheet.STOCK_SHEET_HEADER == [
        "ItemID",
        "ItemName",
        "Price",
        "Inventory",
        "Sales",
        "Revenue",
    ]