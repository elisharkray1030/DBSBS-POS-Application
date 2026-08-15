"""UI layer — the setup screen. Untested by design (docs/spec.md)."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from pos.domain import PosError, money

from .dialogs import show_error


class SetupScreen(ttk.Frame):
    """Load the catalog CSV, enter the float and the device name."""

    def __init__(self, master, app) -> None:
        super().__init__(master, padding=24)
        self.app = app
        self.session = app.session

        ttk.Label(self, text="DBS Garden Fete POS — setup", font=("Segoe UI", 16)).pack(
            pady=(0, 16)
        )

        ttk.Label(self, text="Catalog CSV (Name, Price, Quantity):").pack(anchor="w")
        row = ttk.Frame(self)
        row.pack(fill="x", pady=(2, 4))
        self.csv_path = tk.StringVar()
        ttk.Entry(row, textvariable=self.csv_path, width=40).pack(side="left", padx=(0, 4))
        ttk.Button(row, text="Browse...", command=self._browse).pack(side="left")
        self.csv_status = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.csv_status).pack(anchor="w", pady=(0, 8))

        ttk.Label(self, text="Starting float (HK$):").pack(anchor="w")
        self.float_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.float_var, width=12).pack(
            anchor="w", pady=(2, 8)
        )

        ttk.Label(self, text="Device name (e.g. Till A):").pack(anchor="w")
        self.device_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.device_var, width=20).pack(
            anchor="w", pady=(2, 8)
        )

        ttk.Button(self, text="Start the day", command=self._start).pack(
            pady=(8, 0)
        )

        self._loaded = False

    def _browse(self) -> None:
        chosen = filedialog.askopenfilename(
            parent=self,
            title="Choose the catalog CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not chosen:
            return
        self.csv_path.set(chosen)
        try:
            count = self.session.load_catalog(chosen)
        except (PosError, OSError, ValueError) as exc:
            self.csv_status.set(f"Could not load: {exc}")
            self._loaded = False
            return
        self.csv_status.set(f"Loaded {count} items.")
        self._loaded = True

    def _start(self) -> None:
        if not self._loaded:
            messagebox.showwarning(
                "Catalog required", "Load the catalog CSV first."
            )
            return
        try:
            self.session.set_float(money(self.float_var.get()))
            self.session.set_device_name(self.device_var.get())
        except PosError as exc:
            show_error("Cannot start", exc)
            return
        self.app.show_sale()
