"""Guard tests for the shared table-header palette and style application.

The UI layer is otherwise untested by design; this is the one narrow guard
requested by the spec (`.scratch/table-header-contrast-fix/spec.md`). It
exercises the shared styling module's palette accessor and style-application
routine — the single seam every data table in the app funnels through.

Tk and CustomTkinter are required, so the module skips in headless or
unadorned environments and runs where the app actually renders (Windows).
"""

from __future__ import annotations

from contextlib import contextmanager

import pytest

pytest.importorskip("tkinter")
ctk = pytest.importorskip("customtkinter")

import tkinter as tk
from tkinter import ttk

from pos.ui import style

# The item list's column set, as it should read after the Status column goes.
ITEM_COLUMNS = ("item_id", "name", "price", "remaining")
ITEM_HEADINGS = ("ID", "Item", "Price", "Remaining")


@contextmanager
def _tk_root():
    """A withdrawn Tk root, skipping when there is no display to render on."""
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"No display for Tk: {exc}")
    root.withdraw()
    try:
        yield root
    finally:
        root.destroy()

# WCAG AA contrast floor for normal-size text (locked in the spec).
AA_MIN_CONTRAST = 4.5

# Header pairs locked by grilling consensus and recorded in the spec —
# independent, known-good literals, not derived from the code under test.
LOCKED_HEADER_PAIRS = {
    "light": ("#dbe4ee", "#0f172a"),
    "dark": ("#333333", "#ffffff"),
}


def _linearize(channel: float) -> float:
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def _relative_luminance(hex_color: str) -> float:
    channels = (int(hex_color.lstrip("#")[i : i + 2], 16) / 255 for i in (0, 2, 4))
    r, g, b = (_linearize(c) for c in channels)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(fg: str, bg: str) -> float:
    l1, l2 = _relative_luminance(fg), _relative_luminance(bg)
    light, dark = max(l1, l2), min(l1, l2)
    return (light + 0.05) / (dark + 0.05)


@pytest.mark.parametrize("mode", ["light", "dark"])
def test_palette_exposes_the_locked_header_pair(mode: str) -> None:
    ctk.set_appearance_mode(mode)
    header_bg, header_fg = LOCKED_HEADER_PAIRS[mode]
    assert style.palette()["header_bg"] == header_bg
    assert style.palette()["header_fg"] == header_fg


@pytest.mark.parametrize("mode", ["light", "dark"])
def test_header_pair_meets_wcag_aa_contrast(mode: str) -> None:
    header_bg, header_fg = LOCKED_HEADER_PAIRS[mode]
    assert _contrast_ratio(header_fg, header_bg) >= AA_MIN_CONTRAST


@pytest.mark.parametrize("mode", ["light", "dark"])
def test_header_bar_is_distinct_from_the_body(mode: str) -> None:
    ctk.set_appearance_mode(mode)
    palette = style.palette()
    assert palette["header_bg"] != palette["bg"]


@pytest.mark.parametrize("mode", ["light", "dark"])
def test_treeview_heading_style_carries_the_palette_values(mode: str) -> None:
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"No display for Tk: {exc}")
    root.withdraw()
    try:
        ctk.set_appearance_mode(mode)
        style.configure_treeview_style()
        tree_style = ttk.Style()
        if tree_style.theme_use() == "clam":
            header_bg, header_fg = LOCKED_HEADER_PAIRS[mode]
            assert tree_style.lookup("Treeview.Heading", "background") == header_bg
            assert tree_style.lookup("Treeview.Heading", "foreground") == header_fg
    finally:
        root.destroy()


def test_make_table_applies_per_column_widths() -> None:
    with _tk_root() as root:
        baseline = style.make_table(
            root, ITEM_COLUMNS, ITEM_HEADINGS, height=5
        )
        tree = style.make_table(
            root,
            ITEM_COLUMNS,
            ITEM_HEADINGS,
            height=5,
            widths=(70, None, 60, 60),
        )
        assert tree.column("item_id")["width"] == 70
        assert tree.column("price")["width"] == 60
        assert tree.column("remaining")["width"] == 60
        assert tree.column("name")["width"] == baseline.column("name")["width"]


def test_make_table_applies_per_column_anchors() -> None:
    with _tk_root() as root:
        baseline = style.make_table(
            root, ITEM_COLUMNS, ITEM_HEADINGS, height=5
        )
        tree = style.make_table(
            root,
            ITEM_COLUMNS,
            ITEM_HEADINGS,
            height=5,
            anchors=("center", None, "center", "center"),
        )
        assert tree.column("item_id")["anchor"] == "center"
        assert tree.column("price")["anchor"] == "center"
        assert tree.column("remaining")["anchor"] == "center"
        assert tree.column("name")["anchor"] == baseline.column("name")["anchor"]


def test_make_table_applies_per_column_minimum_widths() -> None:
    with _tk_root() as root:
        baseline = style.make_table(
            root, ITEM_COLUMNS, ITEM_HEADINGS, height=5
        )
        tree = style.make_table(
            root,
            ITEM_COLUMNS,
            ITEM_HEADINGS,
            height=5,
            minwidths=(None, 220, None, None),
        )
        assert tree.column("name")["minwidth"] == 220
        assert tree.column("item_id")["minwidth"] == baseline.column("item_id")["minwidth"]
        assert tree.column("price")["minwidth"] == baseline.column("price")["minwidth"]


def test_make_table_applies_per_column_stretch() -> None:
    with _tk_root() as root:
        tree = style.make_table(
            root,
            ITEM_COLUMNS,
            ITEM_HEADINGS,
            height=5,
            stretch=(False, True, False, False),
        )
        assert tree.column("item_id")["stretch"] == 0
        assert tree.column("price")["stretch"] == 0
        assert tree.column("remaining")["stretch"] == 0
        assert tree.column("name")["stretch"] == 1


def test_make_table_without_layout_params_keeps_treeview_defaults() -> None:
    with _tk_root() as root:
        tree = style.make_table(
            root, ITEM_COLUMNS, ITEM_HEADINGS, height=5
        )
        column = tree.column("item_id")
        assert column["width"] == 200
        assert column["minwidth"] == 20
        assert column["stretch"] == 1
        assert column["anchor"] == "w"


def _horizontal_scrollbars(parent) -> list[ttk.Scrollbar]:
    return [
        widget
        for widget in parent.winfo_children()
        if isinstance(widget, ttk.Scrollbar)
        and str(widget.cget("orient")) == "horizontal"
    ]


def test_make_table_horizontal_scroll_wires_a_scrollbar_to_the_table() -> None:
    with _tk_root() as root:
        tree = style.make_table(
            root, ITEM_COLUMNS, ITEM_HEADINGS, height=5, horizontal_scroll=True
        )
        bars = _horizontal_scrollbars(root)
        assert len(bars) == 1
        bar = bars[0]
        assert "xview" in bar.cget("command")
        assert "set" in tree.cget("xscrollcommand")


def test_make_table_without_horizontal_scroll_leaves_table_plain() -> None:
    with _tk_root() as root:
        tree = style.make_table(root, ITEM_COLUMNS, ITEM_HEADINGS, height=5)
        assert _horizontal_scrollbars(root) == []
        assert tree.cget("xscrollcommand") == ""


def test_sold_out_tag_strikes_through_and_dims() -> None:
    with _tk_root() as root:
        ctk.set_appearance_mode("light")
        tree = ttk.Treeview(root, columns=ITEM_COLUMNS, show="headings")
        style.configure_sold_out_tag(tree)
        tag = tree.tag_configure("sold_out")
        assert "overstrike" in tag["font"]
        assert tag["foreground"] == style.palette()["sold_out"]
