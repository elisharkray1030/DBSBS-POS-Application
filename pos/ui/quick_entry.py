"""Pure input parsing for keyboard quick entry on the Sale screen."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

QuickEntryField = Literal["item_id", "quantity"]


@dataclass(frozen=True)
class QuickEntryError:
    """A validation message tied to the quick-entry field that needs attention."""

    field: QuickEntryField
    message: str


_INVALID_QUANTITY = QuickEntryError(
    "quantity", "Qty must be a positive whole number."
)


def parse_item_id(raw: str) -> str | QuickEntryError:
    """Trim surrounding whitespace without interpreting an Item ID as a number."""
    item_id = raw.strip()
    if not item_id:
        return QuickEntryError("item_id", "Enter an Item ID.")
    return item_id


def parse_quantity(raw: str) -> int | QuickEntryError:
    """Resolve blank Qty to one and accept only positive whole-number input."""
    quantity_text = raw.strip()
    if not quantity_text:
        return 1
    if not quantity_text.isdecimal():
        return _INVALID_QUANTITY
    try:
        quantity = int(quantity_text)
    except ValueError:
        return _INVALID_QUANTITY
    if quantity < 1:
        return _INVALID_QUANTITY
    return quantity
