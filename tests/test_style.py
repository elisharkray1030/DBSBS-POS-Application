"""Guard tests for the shared table-header palette and style application.

The UI layer is otherwise untested by design; this is the one narrow guard
requested by the spec (`.scratch/table-header-contrast-fix/spec.md`). It
exercises the shared styling module's palette accessor and style-application
routine — the single seam every data table in the app funnels through.

Tk and CustomTkinter are required, so the module skips in headless or
unadorned environments and runs where the app actually renders (Windows).
"""

from __future__ import annotations

import pytest

pytest.importorskip("tkinter")
ctk = pytest.importorskip("customtkinter")

import tkinter as tk
from tkinter import ttk

from pos.ui import style

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
