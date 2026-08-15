"""08 — CSV export.

Each device exports comma-delimited UTF-8 files with a header row: sales.csv
(one row per sale), items.csv (one row per line item), and the device's Stock
sheet report `stocks-<device>.csv`. Voids appear with a `voided` status;
corrections appear in their final state with their original creation time.
"""

from __future__ import annotations

import csv
from decimal import Decimal

from pos.domain import CASH, OCTOPUS, Tender


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.reader(handle))


def test_export_writes_both_files_with_headers(configured_session, tmp_path):
    configured_session.add_item_to_sale("Mug", 1)
    configured_session.settle_current_sale([Tender(CASH, Decimal("60"), tendered=Decimal("60"))])
    paths = configured_session.export_csv(tmp_path / "export")

    assert paths == [
        tmp_path / "export" / "sales.csv",
        tmp_path / "export" / "items.csv",
        tmp_path / "export" / "stocks-Till A.csv",
    ]
    sales_rows = read_rows(paths[0])
    assert sales_rows[0] == [
        "device", "sale_seq", "created_at", "updated_at", "status",
        "total", "cash", "octopus", "voucher",
    ]
    items_rows = read_rows(paths[1])
    assert items_rows[0] == ["device", "sale_seq", "status", "item", "quantity", "price"]


def test_sales_export_has_one_row_per_sale_with_all_fields(configured_session, tmp_path):
    configured_session.add_item_to_sale("Mug", 1)
    configured_session.settle_current_sale([Tender(CASH, Decimal("60"), tendered=Decimal("60"))])
    configured_session.add_item_to_sale("Badge", 2)
    configured_session.settle_current_sale([Tender(OCTOPUS, Decimal("30"))])

    rows = read_rows(configured_session.export_csv(tmp_path)[0])
    assert len(rows) == 3  # header + 2 sales
    first = rows[1]
    assert first[0] == "Till A"
    assert first[1] == "1"
    assert first[4] == "completed"
    assert first[5] == "60"
    assert first[6] == "60"
    assert first[7] == "0"
    assert first[8] == "0"
    second = rows[2]
    assert second[1] == "2"
    assert second[7] == "30"


def test_items_export_has_one_row_per_line_item(configured_session, tmp_path):
    configured_session.add_item_to_sale("Mug", 2)
    configured_session.add_item_to_sale("Badge", 3)
    configured_session.settle_current_sale([Tender(CASH, Decimal("165"), tendered=Decimal("165"))])

    rows = read_rows(configured_session.export_csv(tmp_path)[1])
    assert len(rows) == 3  # header + 2 line items
    assert rows[1] == ["Till A", "1", "completed", "Mug", "2", "60"]
    assert rows[2] == ["Till A", "1", "completed", "Badge", "3", "15"]


def test_voided_sales_appear_with_voided_status(configured_session, tmp_path):
    configured_session.add_item_to_sale("Mug", 1)
    configured_session.settle_current_sale([Tender(CASH, Decimal("60"), tendered=Decimal("60"))])
    configured_session.void_sale(1)

    sales_rows = read_rows(configured_session.export_csv(tmp_path)[0])
    assert sales_rows[1][4] == "voided"
    assert sales_rows[1][1] == "1"
    items_rows = read_rows(configured_session.export_csv(tmp_path)[1])
    assert len(items_rows) == 2  # the voided sale's line item is still present
    assert items_rows[1][0] == "Till A"
    assert items_rows[1][2] == "voided"
    assert items_rows[1][3] == "Mug"


def test_corrected_sales_export_final_state_with_original_creation_time(
    configured_session, tmp_path, clock
):
    configured_session.add_item_to_sale("Mug", 1)
    configured_session.settle_current_sale([Tender(CASH, Decimal("60"), tendered=Decimal("60"))])
    created = configured_session.get_sale(1).created_at.isoformat()
    clock.advance(minutes=20)
    configured_session.correct_sale(
        seq=1,
        line_items=[_line_item(configured_session, "Badge", 4)],
        tenders=[Tender(CASH, Decimal("60"), tendered=Decimal("60"))],
    )

    row = read_rows(configured_session.export_csv(tmp_path)[0])[1]
    assert row[2] == created
    assert row[3] != created  # updated time differs
    assert row[5] == "60"


def _line_item(session, name, qty):
    from tests.helpers import line_item

    return line_item(session, name, qty)
