"""Domain types for the DBS Garden Fete POS.

Vocabulary follows CONTEXT.md. Money is `Decimal` throughout; prices are
whole Hong Kong dollars but cents are handled safely.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

Money = Decimal

# Sale statuses
COMPLETED = "completed"
VOIDED = "voided"

# Tender methods
CASH = "cash"
OCTOPUS = "octopus"
VOUCHER = "voucher"


class PosError(Exception):
    """Base class for domain errors."""


class SetupError(PosError):
    """Raised when the session is used before it is configured."""


class CatalogError(PosError):
    """Raised when catalog data is malformed."""


class InvalidSettlement(PosError):
    """Raised when a settlement does not respect the payment rules."""


class ItemNotFound(PosError):
    """Raised when an item ID does not exist in the catalog."""


class ItemSoldOut(PosError):
    """Raised when a sold-out item is added to a sale."""


class SaleNotFound(PosError):
    """Raised when a sale sequence number does not exist."""


def money(value: str | Decimal | float) -> Money:
    """Coerce a value to a Decimal, raising for non-numeric input."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    text = str(value).strip()
    if not text:
        raise CatalogError(f"Not a money value: {value!r}")
    try:
        return Decimal(text)
    except Exception as exc:
        raise CatalogError(f"Not a money value: {value!r}") from exc


@dataclass
class Item:
    """A physical object sold at a fixed price (CONTEXT.md: Item).

    `item_id` is the item's canonical identity, carried from the organizer's
    Stock sheet (CONTEXT.md: Item ID). It is unique within the sheet and never
    assigned in-app. Source-cell preservation lives in the Stock sheet module,
    not on the domain item.
    """

    item_id: str
    name: str
    price: Money
    starting_quantity: int | None = None
    sold_out: bool = False


@dataclass
class ItemStock:
    """An item as shown in the item list, with its live remaining count.

    `remaining` is starting quantity minus what this device has sold
    (non-void, final-state). It is None when the item has no starting
    quantity. The app never infers sold-out from remaining.
    """

    item_id: str
    name: str
    price: Money
    starting_quantity: int | None
    remaining: int | None
    sold_out: bool


@dataclass
class LineItem:
    """One item line on a sale.

    `item_id` is the identity of the item (CONTEXT.md: Item ID) so a sale can
    always be traced back to exactly one row of the master file; `item_name`
    is the display name at the time the line was settled.
    """

    item_id: str
    item_name: str
    quantity: int
    price: Money  # unit price, fixed at the time the line was settled

    @property
    def total(self) -> Money:
        return self.price * self.quantity


@dataclass
class Tender:
    """A payment portion of a sale (CONTEXT.md: Split settlement).

    `method` is one of CASH, OCTOPUS, VOUCHER. `amount` is the portion of
    the sale total this method covers. `tendered` is the cash handed over
    for a cash portion (used to compute change); None means change is 0.
    """

    method: str
    amount: Money
    tendered: Money | None = None


@dataclass
class Sale:
    """A single customer's purchase (CONTEXT.md: Sale).

    Sequence numbers are per-device and never reused. A correction keeps the
    original sequence number and creation time but gains an updated time; a
    void keeps its original number too.
    """

    seq: int
    created_at: datetime
    updated_at: datetime
    status: str
    line_items: list[LineItem]
    tenders: list[Tender]
    device_name: str

    @property
    def total(self) -> Money:
        return sum((line.total for line in self.line_items), Decimal("0"))

    def tender_sum(self, method: str) -> Money:
        return sum(
            (t.amount for t in self.tenders if t.method == method),
            Decimal("0"),
        )


@dataclass
class CashAdjustment:
    """Cash added to or removed from the till mid-day (CONTEXT.md).

    `amount` is signed: positive is cash added, negative is cash removed.
    """

    amount: Money
    reason: str
    created_at: datetime


@dataclass
class Settings:
    """Per-device setup state (CONTEXT.md: Device, Float, Catalog)."""

    device_name: str = ""
    float_amount: Money | None = None
    catalog: list[Item] = field(default_factory=list)
    source_cells: dict[str, tuple[str, str, str, str]] = field(default_factory=dict)
    last_export_at: datetime | None = None

    @property
    def is_configured(self) -> bool:
        return (
            bool(self.device_name)
            and self.float_amount is not None
            and bool(self.catalog)
        )

    def item_by_id(self, item_id: str) -> Item | None:
        for item in self.catalog:
            if item.item_id == item_id:
                return item
        return None

    def source_cells_for(self, item_id: str) -> tuple[str, str, str, str] | None:
        return self.source_cells.get(item_id)


@dataclass
class SettlementResult:
    """Returned when a sale is settled."""

    seq: int
    total: Money
    change_due: Money
    created_at: datetime
    tenders: list[Tender]


@dataclass
class RunningSummary:
    """Today's takings and sale count on the sale screen.

    Excludes voids; reflects corrections' final state.
    """

    takings: Money
    sale_count: int


@dataclass
class EndOfDay:
    """Per-device end-of-day reconciliation figures (CONTEXT.md)."""

    expected_cash: Money
    octopus_total: Money
    voucher_total: Money
    sold_counts: dict[str, int]  # keyed by Item ID
    voids: list[Sale]
    cash_adjustments: list[CashAdjustment]
