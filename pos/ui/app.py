"""UI layer — the application shell and screen switching. Untested by design
(docs/spec.md)."""

from __future__ import annotations

import customtkinter as ctk  # type: ignore[import-untyped]

from pos.app_errors import CallbackFailureHandler

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
        self._callback_failures = CallbackFailureHandler()
        self.title("DBS Garden Fete POS")
        self.geometry("1000x700")
        self.minsize(800, 600)  # floor for the item-list columns, derived from the locked layout (U4 spec #52)
        self._current = None
        style.configure_treeview_style()
        style.start_appearance_watcher(self, self._on_appearance_change)
        if session.is_configured():
            self.show_sale()
        else:
            self.show_setup()

    def report_callback_exception(self, exc, val, tb):
        """Route an exception raised inside a Tk callback (spec #81, ticket 02).

        Tk calls this on the root widget when a screen callback raises; the
        failure is logged and shown in at most one fatal dialog, so a
        mid-event crash does not fail silently.
        """
        self._callback_failures.handle(val)

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
