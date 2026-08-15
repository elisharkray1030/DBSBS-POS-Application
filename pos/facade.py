"""The POS session facade — the single test seam (docs/spec.md §Testing).

The UI layer talks only to this object. All tests drive it as a black box
with an `InMemoryPersistence` backing; the production app injects
`SqlitePersistence`. The facade holds the in-progress sale and the device
settings, and persists every completed sale immediately.
"""

from __future__ import annotations

import csv
from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from . import catalog as catalog_module
from .domain import (
    CASH,
    COMPLETED,
    OCTOPUS,
    VOIDED,
    VOUCHER,
    CashAdjustment,
    EndOfDay,
    InvalidSettlement,
    Item,
    ItemNotFound,
    ItemSoldOut,
    ItemStock,
    LineItem,
    Money,
    PosError,
    RunningSummary,
    Sale,
    SaleNotFound,
    Settings,
    SettlementResult,
    SetupError,
    Tender,
    money,
)

Clock = Callable[[], datetime]


def _validate_tenders(tenders: list[Tender], total: Decimal) -> None:
    if not tenders:
        raise InvalidSettlement("A settlement needs at least one tender")
    for tender in tenders:
        if tender.method not in (CASH, OCTOPUS, VOUCHER):
            raise InvalidSettlement(f"Unknown tender method: {tender.method!r}")
        if tender.amount <= 0:
            raise InvalidSettlement("A tender amount must be positive")
        if tender.method == CASH:
            if tender.tendered is None:
                raise InvalidSettlement(
                    "Cash tendered must be recorded for a cash tender"
                )
            if tender.tendered < tender.amount:
                raise InvalidSettlement(
                    "Cash tendered cannot be less than the cash portion"
                )
    tender_total = sum((t.amount for t in tenders), Decimal("0"))
    if tender_total != total:
        raise InvalidSettlement(
            f"Tenders total {tender_total} but the sale is {total}"
        )
    octopus = [t for t in tenders if t.method == OCTOPUS]
    if octopus and len(octopus) > 1:
        raise InvalidSettlement("A sale can have only one Octopus tender")
    if octopus:
        if len(tenders) != 1:
            raise InvalidSettlement("Octopus must settle the full sale on its own")
        if octopus[0].amount != total:
            raise InvalidSettlement(
                "Octopus must equal the full sale amount; partial Octopus is rejected"
            )


def _change_due(tenders: list[Tender]) -> Decimal:
    return sum(
        (
            t.tendered - t.amount
            for t in tenders
            if t.method == CASH and t.tendered is not None
        ),
        Decimal("0"),
    )


class PosSession:
    def __init__(self, persistence, clock: Clock | None = None) -> None:
        self._persistence = persistence
        self._clock: Clock = clock or datetime.now
        self._settings = persistence.load_settings() or Settings()
        self._current_items: list[LineItem] = []

    # -- helpers ------------------------------------------------------------

    def _now(self) -> datetime:
        return self._clock()

    def _save_settings(self) -> None:
        self._persistence.save_settings(self._settings)

    def _find_item(self, item_id: str) -> Item:
        item = self._settings.item_by_id(item_id)
        if item is None:
            raise ItemNotFound(f"No item with ID {item_id!r} in the catalog")
        return item

    def _require_configured(self) -> None:
        if not self._settings.is_configured:
            raise SetupError("The device is not set up yet")

    def _completed_sales(self) -> list[Sale]:
        return [s for s in self._persistence.get_sales() if s.status == COMPLETED]

    # -- setup --------------------------------------------------------------

    def set_device_name(self, name: str) -> None:
        name = name.strip()
        if not name:
            raise SetupError("Device name cannot be empty")
        self._settings.device_name = name
        self._save_settings()

    def set_float(self, amount: str | Decimal | float) -> None:
        value = money(amount)
        if value < 0:
            raise SetupError("Float cannot be negative")
        self._settings.float_amount = value
        self._save_settings()

    def load_catalog(self, path: str | Path) -> int:
        items = catalog_module.load_catalog(path)
        if not items:
            raise PosError("The Stock sheet CSV contains no items")
        self._settings.catalog = items
        self._save_settings()
        return len(items)

    def is_configured(self) -> bool:
        return self._settings.is_configured

    def device_name(self) -> str:
        return self._settings.device_name

    def float_amount(self) -> Decimal | None:
        return self._settings.float_amount

    # -- catalog / items ----------------------------------------------------

    def list_items(self) -> list[ItemStock]:
        sold_by_item = self._sold_and_revenue_by_item()
        stocks: list[ItemStock] = []
        for item in self._settings.catalog:
            remaining = None
            if item.starting_quantity is not None:
                remaining = item.starting_quantity - sold_by_item.get(
                    item.item_id, (0, Decimal("0"))
                )[0]
            stocks.append(
                ItemStock(
                    item_id=item.item_id,
                    name=item.name,
                    price=item.price,
                    starting_quantity=item.starting_quantity,
                    remaining=remaining,
                    sold_out=item.sold_out,
                )
            )
        return stocks

    def mark_sold_out(self, item_id: str) -> None:
        self._find_item(item_id).sold_out = True
        self._save_settings()

    def unmark_sold_out(self, item_id: str) -> None:
        self._find_item(item_id).sold_out = False
        self._save_settings()

    def is_sold_out(self, item_id: str) -> bool:
        return self._find_item(item_id).sold_out

    # -- building the current sale ------------------------------------------

    def begin_sale(self) -> None:
        self._current_items = []

    def current_sale_items(self) -> list[LineItem]:
        return list(self._current_items)

    def current_sale_total(self) -> Decimal:
        return sum((line.total for line in self._current_items), Decimal("0"))

    def add_item_to_sale(self, item_id: str, quantity: int) -> None:
        quantity = int(quantity)
        if quantity <= 0:
            raise PosError("Quantity must be a positive whole number")
        item = self._find_item(item_id)
        if item.sold_out:
            raise ItemSoldOut(f"{item.name!r} is sold out")
        for line in self._current_items:
            if line.item_id == item_id:
                line.quantity += quantity
                return
        self._current_items.append(
            LineItem(item_id=item.item_id, item_name=item.name, quantity=quantity, price=item.price)
        )

    def set_sale_quantity(self, item_id: str, quantity: int) -> None:
        quantity = int(quantity)
        if quantity < 0:
            raise PosError("Quantity cannot be negative")
        if quantity == 0:
            self._current_items = [
                line for line in self._current_items if line.item_id != item_id
            ]
            return
        item = self._find_item(item_id)
        if item.sold_out:
            raise ItemSoldOut(f"{item.name!r} is sold out")
        for line in self._current_items:
            if line.item_id == item_id:
                line.quantity = quantity
                return
        self._current_items.append(
            LineItem(item_id=item.item_id, item_name=item.name, quantity=quantity, price=item.price)
        )

    # -- settling -----------------------------------------------------------

    def settle_current_sale(self, tenders: list[Tender]) -> SettlementResult:
        self._require_configured()
        if not self._current_items:
            raise InvalidSettlement("The current sale has no items")
        total = self.current_sale_total()
        _validate_tenders(tenders, total)
        seq = self._persistence.next_sale_sequence()
        now = self._now()
        sale = Sale(
            seq=seq,
            created_at=now,
            updated_at=now,
            status=COMPLETED,
            line_items=list(self._current_items),
            tenders=list(tenders),
            device_name=self._settings.device_name,
        )
        self._persistence.save_sale(sale)
        self._current_items = []
        return SettlementResult(
            seq=seq,
            total=total,
            change_due=_change_due(tenders),
            created_at=now,
            tenders=list(tenders),
        )

    # -- recorded sales: corrections and voids ------------------------------

    def get_sale(self, seq: int) -> Sale:
        for sale in self._persistence.get_sales():
            if sale.seq == int(seq):
                return sale
        raise SaleNotFound(f"No sale with sequence number {seq}")

    def list_sales(self) -> list[Sale]:
        return self._persistence.get_sales()

    def correct_sale(
        self,
        seq: int,
        line_items: list[LineItem],
        tenders: list[Tender],
    ) -> None:
        existing = self.get_sale(seq)
        if existing.status != COMPLETED:
            raise PosError("A voided sale cannot be corrected")
        if not line_items:
            raise InvalidSettlement("A corrected sale must have items")
        total = sum((line.total for line in line_items), Decimal("0"))
        _validate_tenders(tenders, total)
        corrected = Sale(
            seq=existing.seq,
            created_at=existing.created_at,
            updated_at=self._now(),
            status=COMPLETED,
            line_items=list(line_items),
            tenders=list(tenders),
            device_name=existing.device_name,
        )
        self._persistence.save_sale(corrected)

    def void_sale(self, seq: int) -> None:
        existing = self.get_sale(seq)
        if existing.status != COMPLETED:
            raise PosError("That sale is already voided")
        voided = Sale(
            seq=existing.seq,
            created_at=existing.created_at,
            updated_at=self._now(),
            status=VOIDED,
            line_items=list(existing.line_items),
            tenders=list(existing.tenders),
            device_name=existing.device_name,
        )
        self._persistence.save_sale(voided)

    def list_voids(self) -> list[Sale]:
        return [s for s in self._persistence.get_sales() if s.status != COMPLETED]

    # -- cash adjustments ---------------------------------------------------

    def record_cash_adjustment(self, amount: str | Decimal | float, reason: str) -> None:
        self._require_configured()
        value = money(amount)
        reason = reason.strip()
        if value == 0:
            raise PosError("A cash adjustment must be non-zero")
        if not reason:
            raise PosError("A cash adjustment needs a reason")
        self._persistence.save_cash_adjustment(
            CashAdjustment(amount=value, reason=reason, created_at=self._now())
        )

    def list_cash_adjustments(self) -> list[CashAdjustment]:
        return self._persistence.get_cash_adjustments()

    # -- queries ------------------------------------------------------------

    def running_summary(self) -> RunningSummary:
        self._require_configured()
        completed = self._completed_sales()
        return RunningSummary(
            takings=sum((s.total for s in completed), Decimal("0")),
            sale_count=len(completed),
        )

    def end_of_day(self) -> EndOfDay:
        self._require_configured()
        float_amount = self._settings.float_amount
        if float_amount is None:
            raise SetupError("No float recorded")
        completed = self._completed_sales()
        cash = sum((s.tender_sum(CASH) for s in completed), Decimal("0"))
        octopus = sum((s.tender_sum(OCTOPUS) for s in completed), Decimal("0"))
        voucher = sum((s.tender_sum(VOUCHER) for s in completed), Decimal("0"))
        sold_counts: dict[str, int] = {}
        for item_id, (units, _revenue) in self._sold_and_revenue_by_item().items():
            if units:
                sold_counts[item_id] = sold_counts.get(item_id, 0) + units
        adjustments = self._persistence.get_cash_adjustments()
        adjustment_sum = sum((a.amount for a in adjustments), Decimal("0"))
        voids = self.list_voids()
        return EndOfDay(
            expected_cash=float_amount + cash + adjustment_sum,
            octopus_total=octopus,
            voucher_total=voucher,
            sold_counts=sold_counts,
            voids=voids,
            cash_adjustments=adjustments,
        )

    # -- export -------------------------------------------------------------

    def _sold_and_revenue_by_item(self) -> dict[str, tuple[int, Money]]:
        """Final-state, non-void units and recorded revenue per item ID.

        Corrections appear in their final state (one record per sale); voided
        sales are excluded. Revenue is the actually-recorded settled value
        (the line total at the time the sale was recorded).
        """
        sold: dict[str, tuple[int, Money]] = {}
        for sale in self._completed_sales():
            for line in sale.line_items:
                units, revenue = sold.get(line.item_id, (0, Decimal("0")))
                sold[line.item_id] = (units + line.quantity, revenue + line.total)
        return sold

    def export_csv(self, directory: str | Path) -> list[Path]:
        self._require_configured()
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        sales_path = directory / "sales.csv"
        items_path = directory / "items.csv"
        report_path = directory / f"stocks-{self._settings.device_name}.csv"
        sales = self._persistence.get_sales()

        with open(sales_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                ["device", "sale_seq", "created_at", "updated_at", "status",
                 "total", "cash", "octopus", "voucher"]
            )
            for sale in sales:
                writer.writerow(
                    [
                        sale.device_name,
                        sale.seq,
                        sale.created_at.isoformat(),
                        sale.updated_at.isoformat(),
                        sale.status,
                        str(sale.total),
                        str(sale.tender_sum(CASH)),
                        str(sale.tender_sum(OCTOPUS)),
                        str(sale.tender_sum(VOUCHER)),
                    ]
                )

        with open(items_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["device", "sale_seq", "status", "item", "quantity", "price"])
            for sale in sales:
                for line in sale.line_items:
                    writer.writerow(
                        [
                            sale.device_name,
                            sale.seq,
                            sale.status,
                            line.item_name,
                            line.quantity,
                            str(line.price),
                        ]
                    )

        with open(report_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(catalog_module.STOCK_SHEET_HEADER)
            sold = self._sold_and_revenue_by_item()
            for item in self._settings.catalog:
                units, revenue = sold.get(item.item_id, (0, Decimal("0")))
                if item.raw_cells is not None:
                    passthrough = list(item.raw_cells)
                else:
                    inventory = (
                        str(item.starting_quantity)
                        if item.starting_quantity is not None
                        else ""
                    )
                    passthrough = [item.item_id, item.name, str(item.price), inventory]
                writer.writerow(passthrough + [str(units), str(revenue)])

        self._settings.last_export_at = self._now()
        self._save_settings()
        return [sales_path, items_path, report_path]

    # -- wipe ---------------------------------------------------------------

    def wipe(self) -> None:
        """Wipe the device, but only after the end-of-day export was taken."""
        latest_record: datetime | None = None
        for sale in self._persistence.get_sales():
            sale_time = max(sale.created_at, sale.updated_at)
            latest_record = (
                sale_time if latest_record is None else max(latest_record, sale_time)
            )
        for adjustment in self._persistence.get_cash_adjustments():
            latest_record = (
                adjustment.created_at
                if latest_record is None
                else max(latest_record, adjustment.created_at)
            )
        last_export = self._settings.last_export_at
        if latest_record is not None and (last_export is None or last_export < latest_record):
            raise PosError(
                "Wipe blocked: take the end-of-day export first so no sale is lost."
            )
        self._persistence.wipe()
        self._settings = Settings()
        self._current_items = []
