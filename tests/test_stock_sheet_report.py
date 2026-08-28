"""03 — Export the completed Stock sheet report.

The end-of-day export writes a third file, named after the device
(`stocks-<device>.csv`), in the master file's six-column shape. ItemID,
ItemName, Price and Inventory pass through unchanged; only Sales (final,
non-void units sold) and Revenue (actually-recorded settled value) are filled.
"""

from __future__ import annotations

import csv
from decimal import Decimal

from pos.domain import CASH, OCTOPUS, Tender
from tests.helpers import line_item


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.reader(handle))


def report_path(configured_session, tmp_path):
    report = [p for p in configured_session.export_csv(tmp_path) if p.name.startswith("stocks-")]
    assert len(report) == 1
    return report[0]


def report_rows(configured_session, tmp_path):
    return {r[0]: r for r in read_rows(report_path(configured_session, tmp_path))[1:]}


def test_export_writes_three_files_including_the_report(configured_session, tmp_path):
    paths = configured_session.export_csv(tmp_path)
    assert len(paths) == 3
    assert paths[0].name == "sales.csv"
    assert paths[1].name == "items.csv"
    assert paths[2].name == "stocks-Till A.csv"


def test_report_header_matches_the_master_file(configured_session, tmp_path):
    rows = read_rows(report_path(configured_session, tmp_path))
    assert rows[0] == ["ItemID", "ItemName", "Price", "Inventory", "Sales", "Revenue"]


def test_report_one_row_per_item_in_master_order(configured_session, tmp_path):
    rows = read_rows(report_path(configured_session, tmp_path))
    assert len(rows) == 4  # header + the 3 catalog items
    assert rows[1] == ["MUG", "Mug", "60", "20", "0", "0"]
    assert rows[2] == ["BDG", "Badge", "15", "50", "0", "0"]
    assert rows[3] == ["PLUSH", "Plush Bear", "120", "", "0", "0"]


def test_report_sales_and_revenue_from_recorded_sales(configured_session, tmp_path):
    configured_session.add_item_to_sale("MUG", 2)
    configured_session.add_item_to_sale("BDG", 3)
    configured_session.settle_current_sale(
        [Tender(CASH, Decimal("165"), tendered=Decimal("165"))]
    )
    rows = report_rows(configured_session, tmp_path)
    assert rows["MUG"][4:] == ["2", "120"]
    assert rows["BDG"][4:] == ["3", "45"]
    assert rows["PLUSH"][4:] == ["0", "0"]


def test_report_reflects_corrections_in_final_state(configured_session, tmp_path):
    configured_session.add_item_to_sale("MUG", 2)
    configured_session.settle_current_sale(
        [Tender(CASH, Decimal("120"), tendered=Decimal("120"))]
    )
    configured_session.correct_sale(
        seq=1,
        line_items=[line_item(configured_session, "Mug", 1)],
        tenders=[Tender(CASH, Decimal("60"), tendered=Decimal("60"))],
    )
    rows = report_rows(configured_session, tmp_path)
    assert rows["MUG"][4:] == ["1", "60"]


def test_report_excludes_voids(configured_session, tmp_path):
    configured_session.add_item_to_sale("MUG", 1)
    configured_session.settle_current_sale(
        [Tender(CASH, Decimal("60"), tendered=Decimal("60"))]
    )
    configured_session.add_item_to_sale("BDG", 1)
    configured_session.settle_current_sale([Tender(OCTOPUS, Decimal("15"))])
    configured_session.void_sale(1)
    rows = report_rows(configured_session, tmp_path)
    assert rows["MUG"][4:] == ["0", "0"]
    assert rows["BDG"][4:] == ["1", "15"]


def test_master_file_is_never_modified(configured_session, catalog_file, tmp_path):
    original = catalog_file.read_text(encoding="utf-8")
    configured_session.export_csv(tmp_path)
    assert catalog_file.read_text(encoding="utf-8") == original


def test_report_echoes_source_cells_verbatim(session, tmp_path):
    sheet = tmp_path / "stock.csv"
    sheet.write_text(
        "ItemID,ItemName,Price,Inventory,Sales,Revenue\n"
        "MUG,  Mug  ,60.00,020,0,0\n"
        "BDG,Badge,15.0,50,0,0\n",
        encoding="utf-8",
    )
    session.set_device_name("Till A")
    session.set_float(500)
    session.load_catalog(sheet)
    report = [p for p in session.export_csv(tmp_path) if p.name.startswith("stocks-")]
    assert len(report) == 1
    rows = read_rows(report[0])
    assert rows[1] == ["MUG", "  Mug  ", "60.00", "020", "0", "0"]
    assert rows[2] == ["BDG", "Badge", "15.0", "50", "0", "0"]


def test_duplicate_names_trace_to_the_right_master_row(session, tmp_path):
    sheet = tmp_path / "stock.csv"
    sheet.write_text(
        "ItemID,ItemName,Price,Inventory,Sales,Revenue\n"
        "MUG-A,Mug,60,10,0,0\n"
        "MUG-B,Mug,90,10,0,0\n",
        encoding="utf-8",
    )
    session.set_device_name("Till A")
    session.set_float(500)
    session.load_catalog(sheet)
    session.add_item_to_sale("MUG-B", 1)
    session.settle_current_sale([Tender(CASH, Decimal("90"), tendered=Decimal("90"))])
    report = [p for p in session.export_csv(tmp_path) if p.name.startswith("stocks-")]
    assert len(report) == 1
    rows = {r[0]: r for r in read_rows(report[0])[1:]}
    assert rows["MUG-A"][4:] == ["0", "0"]
    assert rows["MUG-B"][4:] == ["1", "90"]
