"""The fatal startup error dialog. Windows glue; untested by design."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox


def fatal_error(message: str) -> None:
    root = tk.Tk()
    root.withdraw()
    try:
        messagebox.showerror("DBS Garden Fete POS", message)
    finally:
        root.destroy()
