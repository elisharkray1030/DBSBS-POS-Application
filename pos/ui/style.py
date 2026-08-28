"""Shared styling for the data tables (ttk.Treeview) and common look.

CustomTkinter has no native table widget, so the six data tables stay
ttk.Treeview and are restyled here to match the app's CTk color scheme:
themed headers, accent-colored selection, adequate row height and readable
typography. Colors adapt to the active appearance mode (light/dark) and are
re-applied when the OS theme changes while the app is running.

Fonts and accent colors used across screens and dialogs are defined here so
the app looks consistent in one place.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import customtkinter as ctk  # type: ignore[import-untyped]

# Fonts
FONT_TITLE = ("Segoe UI", 16)
FONT_HEADING = ("Segoe UI", 14)
FONT_SECTION = ("Segoe UI", 12, "bold")
FONT_SUBTITLE = ("Segoe UI", 12)
FONT_TOTAL = ("Segoe UI", 20, "bold")
FONT_BUTTON = ("Segoe UI", 14, "bold")

# Accent colors for prominent actions (semantic: go / stop)
SETTLE_COLOR = "#2e8b57"
SETTLE_HOVER = "#276f46"
WIPE_COLOR = "#b04545"
WIPE_HOVER = "#8f3737"

_TABLE_FONT = ("Segoe UI", 10)
_HEADER_FONT = ("Segoe UI", 10, "bold")

_COLORS = {
    "light": {
        "bg": "#ffffff",
        "fg": "#1a1a1a",
        "field": "#f7f7f7",
        "header_bg": "#dbe4ee",
        "header_fg": "#1a1a1a",
        "select_bg": "#3b8ed0",
        "select_fg": "#ffffff",
        "sold_out": "#9e9e9e",
    },
    "dark": {
        "bg": "#242424",
        "fg": "#e6e6e6",
        "field": "#2b2b2b",
        "header_bg": "#333333",
        "header_fg": "#e6e6e6",
        "select_bg": "#3b8ed0",
        "select_fg": "#ffffff",
        "sold_out": "#6e6e6e",
    },
}


def palette() -> dict[str, str]:
    mode = "dark" if ctk.get_appearance_mode().lower() == "dark" else "light"
    return _COLORS[mode]


def configure_treeview_style() -> None:
    """Apply the current appearance mode's colors to the shared styles."""
    c = palette()
    style = ttk.Style()
    style.configure(
        "Treeview",
        font=_TABLE_FONT,
        rowheight=28,
        background=c["bg"],
        fieldbackground=c["field"],
        foreground=c["fg"],
        borderwidth=0,
    )
    style.map(
        "Treeview",
        background=[("selected", c["select_bg"])],
        foreground=[("selected", c["select_fg"])],
    )
    style.configure(
        "Treeview.Heading",
        font=_HEADER_FONT,
        background=c["header_bg"],
        foreground=c["header_fg"],
    )
    style.map(
        "Treeview.Heading",
        background=[("active", c["header_bg"])],
        foreground=[("active", c["header_fg"])],
    )


def make_table(
    parent, columns: tuple[str, ...], headings: tuple[str, ...], height: int
) -> ttk.Treeview:
    """Build a Treeview with the app's shared styling and column headings."""
    tree = ttk.Treeview(parent, columns=columns, show="headings", height=height)
    for col, text in zip(columns, headings):
        tree.heading(col, text=text)
    return tree


def configure_sold_out_tag(tree: ttk.Treeview) -> None:
    """Dim sold-out rows with a color that fits the current appearance mode."""
    tree.tag_configure("sold_out", foreground=palette()["sold_out"])


def start_appearance_watcher(root: tk.Misc, on_change) -> None:
    """Poll the OS appearance mode and re-apply table styling when it changes.

    CustomTkinter recolors its own widgets automatically; only the raw
    Treeview styles need this manual refresh.
    """

    state = {"mode": ctk.get_appearance_mode().lower()}

    def _poll() -> None:
        mode = ctk.get_appearance_mode().lower()
        if mode != state["mode"]:
            state["mode"] = mode
            configure_treeview_style()
            on_change()
        root.after(1000, _poll)

    root.after(1000, _poll)
