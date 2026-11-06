from pos.ui.labels import stock_sheet_label


def test_stock_sheet_label_shows_filename():
    assert stock_sheet_label("active.csv") == "Stock sheet: active.csv"


def test_stock_sheet_label_reports_missing_source():
    assert stock_sheet_label(None) == "Stock sheet: Source not recorded"
