"""Isolated tests for the end-of-event reporting module (spec #29).

The reporting module is the secondary test seam: it owns the final-state
aggregation, the end-of-day figures, and the three CSV exports. Sales are
built directly as domain objects; corrections appear in their final state
(one record per sale, same sequence number), voids carry the `voided` status.
"""

from __future__ import annotations

import csv
import os
from datetime import datetime
from decimal import Decimal

import pytest

from pos import reporting
from pos.domain import (
    CASH,
    COMPLETED,
    OCTOPUS,
    VOIDED,
    VOUCHER,
    CashAdjustment,
    Item,
    LineItem,
    PosError,
    Sale,
    Tender,
)

T0 = datetime(2026, 8, 15, 9, 0, 0)

CATALOG = [
    Item(item_id="MUG", name="Mug", price=Decimal("60"), starting_quantity=20),
    Item(item_id="BDG", name="Badge", price=Decimal("15"), starting_quantity=50),
    Item(item_id="PLUSH", name="Plush Bear", price=Decimal("120")),
]


def _sale(
    seq: int,
    lines: list[tuple[str, str, int, str]],
    tenders: list[Tender],
    status: str = COMPLETED,
) -> Sale:
    return Sale(
        seq=seq,
        created_at=T0,
        updated_at=T0,
        status=status,
        line_items=[
            LineItem(
                item_id=item_id, item_name=name, quantity=qty, price=Decimal(price)
            )
            for item_id, name, qty, price in lines
        ],
        tenders=tenders,
        device_name="Till A",
    )


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.reader(handle))


# -- aggregation (T1) -------------------------------------------------------


def test_aggregate_counts_corrected_sales_once_in_final_state():
    sales = [
        _sale(
            1,
            [("MUG", "Mug", 1, "60")],
            [Tender(CASH, Decimal("60"), tendered=Decimal("60"))],
        ),
        _sale(
            2,
            [("BDG", "Badge", 2, "15")],
            [Tender(CASH, Decimal("30"), tendered=Decimal("30"))],
        ),
    ]
    sold = reporting.aggregate_sold_and_revenue(sales)
    assert sold == {"MUG": (1, Decimal("60")), "BDG": (2, Decimal("30"))}


def test_aggregate_excludes_voids():
    sales = [
        _sale(
            1,
            [("MUG", "Mug", 2, "60")],
            [Tender(CASH, Decimal("120"), tendered=Decimal("120"))],
            status=VOIDED,
        ),
        _sale(
            2,
            [("BDG", "Badge", 1, "15")],
            [Tender(CASH, Decimal("15"), tendered=Decimal("15"))],
        ),
    ]
    sold = reporting.aggregate_sold_and_revenue(sales)
    assert sold == {"BDG": (1, Decimal("15"))}


# -- end-of-day figures (T1) ------------------------------------------------


def test_end_of_day_tender_totals_and_expected_cash():
    sales = [
        _sale(
            1,
            [("MUG", "Mug", 1, "60")],
            [Tender(CASH, Decimal("60"), tendered=Decimal("60"))],
        ),
        _sale(2, [("MUG", "Mug", 1, "60")], [Tender(OCTOPUS, Decimal("60"))]),
        _sale(3, [("BDG", "Badge", 1, "15")], [Tender(VOUCHER, Decimal("15"))]),
    ]
    figures = reporting.build_end_of_day(Decimal("500"), sales, [], CATALOG)
    assert figures.expected_cash == Decimal("560")
    assert figures.octopus_total == Decimal("60")
    assert figures.voucher_total == Decimal("15")


def test_end_of_day_expected_cash_with_adjustments():
    sales = [
        _sale(
            1,
            [("MUG", "Mug", 1, "60")],
            [Tender(CASH, Decimal("60"), tendered=Decimal("60"))],
        )
    ]
    adjustments = [
        CashAdjustment(amount=Decimal("200"), reason="Topping up change", created_at=T0),
        CashAdjustment(amount=Decimal("-30"), reason="Removing notes", created_at=T0),
    ]
    figures = reporting.build_end_of_day(Decimal("500"), sales, adjustments, CATALOG)
    assert figures.expected_cash == Decimal("730")


def test_end_of_day_sold_rows_in_catalog_order_with_names():
    sales = [
        _sale(
            2,
            [("MUG", "Mug", 1, "60")],
            [Tender(CASH, Decimal("60"), tendered=Decimal("60"))],
        ),
        _sale(
            1,
            [("BDG", "Badge", 2, "15")],
            [Tender(CASH, Decimal("30"), tendered=Decimal("30"))],
        ),
        _sale(
            3,
            [("PLUSH", "Plush Bear", 1, "120")],
            [Tender(OCTOPUS, Decimal("120"))],
            status=VOIDED,
        ),
    ]
    figures = reporting.build_end_of_day(Decimal("500"), sales, [], CATALOG)
    assert figures.sold_rows == [
        reporting.ItemSoldRow(item_id="MUG", item_name="Mug", count=1),
        reporting.ItemSoldRow(item_id="BDG", item_name="Badge", count=2),
    ]


def test_end_of_day_sold_rows_fall_back_for_items_missing_from_catalog():
    sales = [
        _sale(
            1,
            [("BDG", "Badge", 1, "15")],
            [Tender(CASH, Decimal("15"), tendered=Decimal("15"))],
        ),
        _sale(
            2,
            [("KEYCHAIN", "Keychain", 1, "10")],
            [Tender(CASH, Decimal("10"), tendered=Decimal("10"))],
        ),
    ]
    figures = reporting.build_end_of_day(Decimal("500"), sales, [], CATALOG)
    assert figures.sold_rows == [
        reporting.ItemSoldRow(item_id="BDG", item_name="Badge", count=1),
        reporting.ItemSoldRow(item_id="KEYCHAIN", item_name="KEYCHAIN", count=1),
    ]


def test_end_of_day_voids_list():
    voided = _sale(
        1,
        [("MUG", "Mug", 1, "60")],
        [Tender(CASH, Decimal("60"), tendered=Decimal("60"))],
        status=VOIDED,
    )
    figures = reporting.build_end_of_day(Decimal("500"), [voided], [], CATALOG)
    assert figures.voids == [voided]
    assert figures.sold_rows == []
    assert figures.expected_cash == Decimal("500")


# -- CSV row builders (T2) --------------------------------------------------


def test_sales_rows_one_row_per_sale():
    sales = [
        _sale(
            1,
            [("MUG", "Mug", 1, "60")],
            [Tender(CASH, Decimal("60"), tendered=Decimal("60"))],
        ),
        _sale(2, [("BDG", "Badge", 1, "15")], [Tender(OCTOPUS, Decimal("15"))]),
    ]
    rows = reporting.sales_rows(sales)
    assert rows[0] == [
        "device", "sale_seq", "created_at", "updated_at", "status",
        "total", "cash", "octopus", "voucher",
    ]
    assert len(rows) == 3
    assert rows[1] == [
        "Till A", "1", T0.isoformat(), T0.isoformat(), "completed", "60", "60", "0", "0",
    ]
    assert rows[2][7] == "15"


def test_item_rows_one_row_per_line_item():
    sales = [
        _sale(
            1,
            [("MUG", "Mug", 2, "60"), ("BDG", "Badge", 3, "15")],
            [Tender(CASH, Decimal("165"), tendered=Decimal("165"))],
        )
    ]
    rows = reporting.item_rows(sales)
    assert rows[0] == ["device", "sale_seq", "status", "item", "quantity", "price"]
    assert rows[1] == ["Till A", "1", "completed", "Mug", "2", "60"]
    assert rows[2] == ["Till A", "1", "completed", "Badge", "3", "15"]


def test_stock_sheet_rows_delegate_to_stock_sheet_builder():
    source_cells = {
        "MUG": ("MUG", "Mug", "60", "20"),
        "BDG": ("BDG", "Badge", "15", "50"),
    }
    sold = {"MUG": (1, Decimal("60"))}
    rows = reporting.stock_sheet_rows(CATALOG, sold, source_cells)
    assert rows[0] == ["ItemID", "ItemName", "Price", "Inventory", "Sales", "Revenue"]
    assert rows[1] == ["MUG", "Mug", "60", "20", "1", "60"]
    assert rows[2] == ["BDG", "Badge", "15", "50", "0", "0"]
    assert rows[3] == ["PLUSH", "Plush Bear", "120", "", "0", "0"]


# -- export coordinator (T2) ------------------------------------------------


def test_write_export_writes_three_files_and_returns_paths(tmp_path):
    sales = [
        _sale(
            1,
            [("MUG", "Mug", 1, "60")],
            [Tender(CASH, Decimal("60"), tendered=Decimal("60"))],
        )
    ]
    source_cells = {"MUG": ("MUG", "Mug", "60", "20")}
    paths = reporting.write_export(
        tmp_path / "export", sales, CATALOG, source_cells, "Till A"
    )
    assert paths == [
        tmp_path / "export" / "sales.csv",
        tmp_path / "export" / "items.csv",
        tmp_path / "export" / "stocks-Till A.csv",
    ]
    for path in paths:
        assert path.exists()
    sales_rows = read_rows(paths[0])
    assert sales_rows[0][0] == "device"
    assert sales_rows[1][4] == "completed"


def test_export_failure_before_rename_leaves_destination_untouched(tmp_path, monkeypatch):
    sales = [
        _sale(
            1,
            [("MUG", "Mug", 1, "60")],
            [Tender(CASH, Decimal("60"), tendered=Decimal("60"))],
        )
    ]
    source_cells = {"MUG": ("MUG", "Mug", "60", "20")}
    dest = tmp_path / "export"
    dest.mkdir()
    for name in ("sales.csv", "items.csv", "stocks-Till A.csv"):
        (dest / name).write_text("OLD", encoding="utf-8")

    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(reporting, "sales_rows", boom)
    with pytest.raises(OSError):
        reporting.write_export(dest, sales, CATALOG, source_cells, "Till A")
    for name in ("sales.csv", "items.csv", "stocks-Till A.csv"):
        assert (dest / name).read_text(encoding="utf-8") == "OLD"


def test_export_temp_write_failure_cleans_up_temp_files(tmp_path, monkeypatch):
    sales = [
        _sale(
            1,
            [("MUG", "Mug", 1, "60")],
            [Tender(CASH, Decimal("60"), tendered=Decimal("60"))],
        )
    ]
    source_cells = {"MUG": ("MUG", "Mug", "60", "20")}
    dest = tmp_path / "export"
    dest.mkdir()
    for name in ("sales.csv", "items.csv", "stocks-Till A.csv"):
        (dest / name).write_text("OLD", encoding="utf-8")

    written = {"count": 0}

    class FailingWriter:
        def writerows(self, rows):
            written["count"] += 1
            if written["count"] == 2:
                raise OSError("disk full")

    monkeypatch.setattr(reporting.csv, "writer", lambda handle: FailingWriter())
    with pytest.raises(OSError):
        reporting.write_export(dest, sales, CATALOG, source_cells, "Till A")
    for name in ("sales.csv", "items.csv", "stocks-Till A.csv"):
        assert (dest / name).read_text(encoding="utf-8") == "OLD"
    assert {p.name for p in dest.iterdir()} == {
        "sales.csv",
        "items.csv",
        "stocks-Till A.csv",
    }


def test_export_rename_failure_names_the_files(tmp_path, monkeypatch):
    sales = [
        _sale(
            1,
            [("MUG", "Mug", 1, "60")],
            [Tender(CASH, Decimal("60"), tendered=Decimal("60"))],
        )
    ]
    source_cells = {"MUG": ("MUG", "Mug", "60", "20")}
    dest = tmp_path / "export"
    dest.mkdir()

    def boom(src, dst):
        raise OSError("rename blocked")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(PosError) as excinfo:
        reporting.write_export(dest, sales, CATALOG, source_cells, "Till A")
    message = str(excinfo.value)
    assert "sales.csv" in message
    assert "items.csv" in message
    assert "stocks-Till A.csv" in message


# -- consistency between figures and exports (T2) ---------------------------


def test_exported_rows_agree_with_end_of_day_figures(tmp_path):
    catalog = [
        Item(item_id="MUG", name="Mug", price=Decimal("60"), starting_quantity=20),
        Item(item_id="BDG", name="Badge", price=Decimal("15"), starting_quantity=50),
    ]
    source_cells = {
        "MUG": ("MUG", "Mug", "60", "20"),
        "BDG": ("BDG", "Badge", "15", "50"),
    }
    corrected = _sale(
        1,
        [("MUG", "Mug", 1, "60")],
        [Tender(CASH, Decimal("60"), tendered=Decimal("60"))],
    )
    voided = _sale(
        2,
        [("BDG", "Badge", 1, "15")],
        [Tender(OCTOPUS, Decimal("15"))],
        status=VOIDED,
    )
    voucher = _sale(3, [("BDG", "Badge", 1, "15")], [Tender(VOUCHER, Decimal("15"))])
    sales = [corrected, voided, voucher]
    adjustments = [
        CashAdjustment(amount=Decimal("200"), reason="Topping up change", created_at=T0),
        CashAdjustment(amount=Decimal("-30"), reason="Removing notes", created_at=T0),
    ]

    figures = reporting.build_end_of_day(Decimal("500"), sales, adjustments, catalog)
    paths = reporting.write_export(
        tmp_path / "export", sales, catalog, source_cells, "Till A"
    )
    sales_export = read_rows(paths[0])
    items_export = read_rows(paths[1])
    report = read_rows(paths[2])

    assert figures.expected_cash == Decimal("730")  # 500 float + 60 cash + 170 adjustments
    assert figures.octopus_total == Decimal("0")  # the Octopus sale was voided
    assert figures.voucher_total == Decimal("15")

    # Sold counts match the Stock sheet report's Sales column.
    report_sales = {row[0]: int(row[4]) for row in report[1:]}
    assert report_sales == {"MUG": 1, "BDG": 1}
    assert [(row.item_id, row.count) for row in figures.sold_rows] == [
        ("MUG", 1),
        ("BDG", 1),
    ]

    # Tender totals match the sales export (excluding voided rows).
    active = [row for row in sales_export[1:] if row[4] == "completed"]
    assert sum(Decimal(row[6]) for row in active) == Decimal("60")
    assert sum(Decimal(row[7]) for row in active) == figures.octopus_total
    assert sum(Decimal(row[8]) for row in active) == figures.voucher_total

    # Voided sales appear only with `voided` status.
    statuses = [row[4] for row in sales_export[1:]]
    assert statuses.count("voided") == 1
    voided_row = next(row for row in sales_export[1:] if row[4] == "voided")
    assert voided_row[1] == "2"
    assert voided_row[7] == "15"  # Octopus amount stays in the audit row
    assert [row[2] for row in items_export[1:]] == ["completed", "voided", "completed"]