"""UI layer — the setup screen. Untested by design (docs/spec.md)."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk  # type: ignore[import-untyped]

from pos import observability
from pos.domain import PosError, money

from . import style
from .dialogs import show_error


class SetupScreen(ctk.CTkFrame):
    """Load the catalog CSV, enter the float and the device name."""

    def __init__(self, master, app) -> None:
        super().__init__(master, corner_radius=0)
        self.app = app
        self.session = app.session

        ctk.CTkLabel(self, text="DBS Garden Fete POS — setup", font=style.FONT_TITLE).pack(
            padx=24, pady=(16, 12)
        )

        ctk.CTkLabel(
            self,
            text="Stock sheet CSV "
            "(ItemID, ItemName, Price, Inventory, Sales, Revenue):",
            anchor="w",
        ).pack(padx=24, fill="x")
        row = ctk.CTkFrame(self)
        row.pack(fill="x", padx=24, pady=(4, 2))
        self.csv_path = tk.StringVar()
        ctk.CTkEntry(
            row, textvariable=self.csv_path, width=320
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(row, text="Browse...", width=100, command=self._browse).pack(
            side="left"
        )
        self.csv_status = tk.StringVar(value="")
        ctk.CTkLabel(
            self, textvariable=self.csv_status, anchor="w", text_color="gray"
        ).pack(padx=24, fill="x", pady=(0, 8))

        ctk.CTkLabel(self, text="Starting float (HK$):", anchor="w").pack(
            padx=24, fill="x"
        )
        self.float_var = tk.StringVar()
        ctk.CTkEntry(self, textvariable=self.float_var, width=120).pack(
            padx=24, anchor="w", pady=(4, 8)
        )

        ctk.CTkLabel(self, text="Device name (e.g. Till A):", anchor="w").pack(
            padx=24, fill="x"
        )
        self.device_var = tk.StringVar()
        ctk.CTkEntry(self, textvariable=self.device_var, width=200).pack(
            padx=24, anchor="w", pady=(4, 8)
        )

        ctk.CTkButton(self, text="Start the day", width=200, command=self._start).pack(
            padx=24, pady=(8, 16)
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
            observability.log_failure("setup catalog", str(exc))
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
            show_error("Cannot start", exc, "setup")
            return
        self.app.show_sale()
