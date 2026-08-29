"""Pure decision logic for inline quantity editing in the Current sale.

Kept free of any Tk import so the guard test runs headlessly anywhere: this is
the one narrow testable seam in an otherwise untested-by-design UI layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

QuantityEditKind = Literal["remove", "set", "revert"]


@dataclass(frozen=True)
class QuantityEdit:
    """The decision a committed inline quantity edit carries.

    `kind` is one of:
    - "remove" — drop the sale line from the Current sale
    - "set"    — replace the line's quantity with `quantity`
    - "revert" — leave the line unchanged (invalid input)
    """

    kind: QuantityEditKind
    quantity: int | None = None


def parse_quantity_edit(raw: str) -> QuantityEdit:
    """Decide what a committed inline edit should do from the raw text.

    "0" removes the line, a positive whole number sets that quantity, and
    empty, non-numeric, or negative input reverts (leaves the line unchanged).
    """
    text = raw.strip()
    if not text:
        return QuantityEdit("revert")
    try:
        value = int(text)
    except ValueError:
        return QuantityEdit("revert")
    if value < 0:
        return QuantityEdit("revert")
    if value == 0:
        return QuantityEdit("remove")
    return QuantityEdit("set", quantity=value)