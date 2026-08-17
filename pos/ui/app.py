"""UI layer — the application shell and screen switching. Untested by design
(docs/spec.md)."""

from __future__ import annotations

import customtkinter as ctk  # type: ignore[import-untyped]

from . import style
from .end_of_day_screen import EndOfDayScreen
from .sale_screen import SaleScreen
from .setup_screen import SetupScreen


class PosApp(ctk.CTk):
    def __init__(self, session) -> None:
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")
        super().__init__()
        self.session = session
        self.title("DBS Garden Fete POS")
        self.geometry("1000x700")
        self._current = None
        style.configure_treeview_style()
        style.start_appearance_watcher(self, self._on_appearance_change)
        if session.is_configured():
            self.show_sale()
        else:
            self.show_setup()

    def _on_appearance_change(self) -> None:
        if self._current is not None and hasattr(self._current, "reapply_theme"):
            self._current.reapply_theme()

    def _replace(self, screen: ctk.CTkFrame) -> None:
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
