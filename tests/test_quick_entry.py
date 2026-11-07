"""Guard tests for the pure Sale-screen quick-entry parser."""

from __future__ import annotations

import pytest

from pos.ui.quick_entry import QuickEntryError, parse_item_id, parse_quantity


def test_item_id_is_trimmed_text_and_preserves_leading_zeroes() -> None:
    assert parse_item_id("  0012  ") == "0012"
    assert parse_item_id("  MUG-B  ") == "MUG-B"


def test_empty_item_id_returns_explicit_error() -> None:
    result = parse_item_id("  ")

    assert isinstance(result, QuickEntryError)
    assert result.field == "item_id"
    assert result.message


def test_blank_quantity_defaults_to_one() -> None:
    assert parse_quantity("  ") == 1


def test_positive_whole_quantity_is_accepted() -> None:
    assert parse_quantity("  12  ") == 12


@pytest.mark.parametrize("raw", ["abc", "2.5", "0", "-3"])
def test_invalid_quantity_returns_explicit_error(raw: str) -> None:
    result = parse_quantity(raw)

    assert isinstance(result, QuickEntryError)
    assert result.field == "quantity"
    assert result.message
