"""Persistence boundary behind the POS session facade.

The facade treats persistence as a black-box store; tests inject
`InMemoryPersistence`, the production app uses `SqlitePersistence`. Both
implement the same operations.
"""

from __future__ import annotations

import copy
from typing import Protocol

from .domain import CashAdjustment, Sale, Settings


class Persistence(Protocol):
    """Storage operations the facade needs."""

    def load_settings(self) -> Settings | None: ...

    def save_settings(self, settings: Settings) -> None: ...

    def next_sale_sequence(self) -> int: ...

    def save_sale(self, sale: Sale) -> None: ...

    def get_sales(self) -> list[Sale]: ...

    def save_cash_adjustment(self, adjustment: CashAdjustment) -> None: ...

    def get_cash_adjustments(self) -> list[CashAdjustment]: ...

    def wipe(self) -> None: ...


class InMemoryPersistence:
    """A store that lives only for the lifetime of the process."""

    def __init__(self) -> None:
        self._settings: Settings | None = None
        self._sales: list[Sale] = []
        self._adjustments: list[CashAdjustment] = []

    def load_settings(self) -> Settings | None:
        return copy.deepcopy(self._settings)

    def save_settings(self, settings: Settings) -> None:
        self._settings = copy.deepcopy(settings)

    def next_sale_sequence(self) -> int:
        return max((sale.seq for sale in self._sales), default=0) + 1

    def save_sale(self, sale: Sale) -> None:
        for i, existing in enumerate(self._sales):
            if existing.seq == sale.seq:
                self._sales[i] = copy.deepcopy(sale)
                break
        else:
            self._sales.append(copy.deepcopy(sale))
        self._sales.sort(key=lambda s: s.seq)

    def get_sales(self) -> list[Sale]:
        return copy.deepcopy(self._sales)

    def save_cash_adjustment(self, adjustment: CashAdjustment) -> None:
        self._adjustments.append(copy.deepcopy(adjustment))

    def get_cash_adjustments(self) -> list[CashAdjustment]:
        return copy.deepcopy(self._adjustments)

    def wipe(self) -> None:
        self._settings = None
        self._sales = []
        self._adjustments = []
