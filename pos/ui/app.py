"""UI layer — the application shell and screen switching. Untested by design
(docs/spec.md)."""

from __future__ import annotations

import tkinter as tk

from .end_of_day_screen import EndOfDayScreen
from .sale_screen import SaleScreen
from .setup_screen import SetupScreen


class PosApp(tk.Tk):
    def __init__(self, session) -> None:
        super().__init__()
        self.session = session
        self.title("DBS Garden Fete POS")
        self.geometry("1000x640")
        self._current: tk.Widget | None = None
        if session.is_configured():
            self.show_sale()
        else:
            self.show_setup()

    def _replace(self, screen: tk.Widget) -> None:
        if self._current is not None:
            self._current.destroy()
        self._current = screen
        screen.pack(fill="both", expand=True)

    def show_setup(self) -> None:
        self._replace(SetupScreen(self, self))

    def show_sale(self) -> None:
        self._replace(SaleScreen(self, self))

    def show_end_of_day(self) -> None:
        self._replace(EndOfDayScreen(self, self))
