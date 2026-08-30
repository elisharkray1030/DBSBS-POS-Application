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


class PersistenceError(PosError):
    """A device database operation failed (CONTEXT.md: Device database)."""


class CorruptRecordError(PersistenceError):
    """Stored data could not be reconstructed into a domain record.

    Raised when a durable record cannot be parsed — malformed JSON, unparseable
    money or timestamps, or a structurally invalid value. The message names the
    offending record (a sale's sequence number, an item id, or a settings key)
    so the damage is findable instead of guessed at.
    """


class SetupError(PosError):
    """Raised when the session is used before it is configured."""


class CatalogError(PosError):
    """Raised when catalog data is malformed."""


class ExportError(PosError):
    """Raised when the end-of-day CSV export cannot be written safely.

    Covers filesystem failures (folder creation, temp writes, renames) and
    an unsafe device name reaching the export. The export dialog displays
    it through the normal error path.
    """


class InvalidMoney(PosError):
    """Raised when a money value is not a finite decimal number.

    Raised by the `money` coercion for non-numeric input and for non-finite
    values (NaN, signaling NaN, positive/negative infinity) regardless of
    input type. The coercion is sign-agnostic: a negative cash adjustment is
    legitimate, so negativity is a rule for the caller, not for money.
    """


class InvalidSettlement(PosError):
    """Raised when a settlement does not respect the payment rules."""


class ItemNotFound(PosError):
    """Raised when an item ID does not exist in the catalog."""


class ItemSoldOut(PosError):
    """Raised when a sold-out item is added to a sale."""


class SaleNotFound(PosError):
    """Raised when a sale sequence number does not exist."""


def money(value: str | Decimal | float) -> Money:
    """Coerce a value to a finite Decimal, raising for non-finite input."""
    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, int):
        result = Decimal(value)
    elif isinstance(value, float):
        result = Decimal(str(value))
    else:
        text = str(value).strip()
        if not text:
            raise InvalidMoney(f"Not a money value: {value!r}")
        try:
            result = Decimal(text)
        except Exception as exc:
            raise InvalidMoney(f"Not a money value: {value!r}") from exc
    if not result.is_finite():
        raise InvalidMoney(f"Not a finite money value: {result}")
    return result


# Device names are embedded in the export as `stocks-<name>.csv`, so they
# must obey the file system's rules (ADR-0005). The register runs only on
# Windows laptops (CONTEXT.md: Device); the rules below are Windows NTFS
# ones, applied as a reject-list so legitimate names such as "Till A" keep
# working.
_ILLEGAL_FILENAME_CHARS = frozenset('<>:"/\\|?*')
_RESERVED_DEVICE_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)
# The device name is embedded in the Stock sheet report file name (ADR-0003,
# ADR-0005). These are the single source for that name's shape.
STOCK_REPORT_FILE_PREFIX = "stocks-"
STOCK_REPORT_FILE_SUFFIX = ".csv"
_MAX_FILENAME_LENGTH = 255  # NTFS maximum per-component length
MAX_DEVICE_NAME_LENGTH = (
    _MAX_FILENAME_LENGTH - len(STOCK_REPORT_FILE_PREFIX) - len(STOCK_REPORT_FILE_SUFFIX)
)


def validate_device_name(name: str) -> str:
    """Trim and validate a device name for safe use in a file name.

    The name becomes the component `stocks-<name>.csv` of the end-of-day
    export (ADR-0005), so it must contain no path separator or traversal, no
    Windows-illegal or control character, no reserved device name, and must
    stay short enough for the export file name to fit the NTFS limit. Returns
    the trimmed name; raises `SetupError` for a name that cannot be used.
    """
    name = name.strip()
    name = name.rstrip(".")
    name = name.strip()
    if not name:
        raise SetupError("Device name cannot be empty")
    if len(name.encode("utf-16-le")) // 2 > MAX_DEVICE_NAME_LENGTH:
        raise SetupError(
            f"Device name is too long for the export file name "
            f"(limit {MAX_DEVICE_NAME_LENGTH} UTF-16 units)"
        )
    if any(ch in _ILLEGAL_FILENAME_CHARS for ch in name):
        raise SetupError(
            "Device name contains characters that are not safe in a file name"
        )
    if any(ord(ch) < 32 for ch in name):
        raise SetupError("Device name contains control characters")
    stem = name.split(".", 1)[0].upper()
    if stem in _RESERVED_DEVICE_NAMES:
        raise SetupError(
            f"{name!r} is a reserved Windows device name and cannot be used"
        )
    return name


# The four source cells (ItemID, ItemName, Price, Inventory) of a Stock sheet
# row exactly as the master file delivered them (CONTEXT.md: Source cells).
SourceCells = tuple[str, str, str, str]


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
    source_cells: dict[str, SourceCells] = field(default_factory=dict)
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

    def source_cells_for(self, item_id: str) -> SourceCells | None:
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
