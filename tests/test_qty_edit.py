"""Guard test for the pure quantity-edit decision helper.

The one narrow UI guard allowed by the canonical spec, mirroring the shared
style guard. Unlike that module, this helper is pure, so the test needs no Tk
and runs in any environment.
"""

from __future__ import annotations

from pos.ui.qty_edit import parse_quantity_edit


def test_zero_means_remove() -> None:
    edit = parse_quantity_edit("0")
    assert edit.kind == "remove"
    assert edit.quantity is None


def test_positive_number_means_set() -> None:
    edit = parse_quantity_edit("12")
    assert edit.kind == "set"
    assert edit.quantity == 12


def test_surrounding_whitespace_is_tolerated() -> None:
    edit = parse_quantity_edit("  5  ")
    assert edit.kind == "set"
    assert edit.quantity == 5


def test_empty_input_reverts() -> None:
    assert parse_quantity_edit("").kind == "revert"


def test_non_numeric_input_reverts() -> None:
    assert parse_quantity_edit("abc").kind == "revert"


def test_negative_input_reverts() -> None:
    assert parse_quantity_edit("-3").kind == "revert"


def test_fractional_input_reverts() -> None:
    assert parse_quantity_edit("2.5").kind == "revert"