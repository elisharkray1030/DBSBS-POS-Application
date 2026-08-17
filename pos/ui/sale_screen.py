"""UI layer — the sale screen. Untested by design (docs/spec.md)."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk  # type: ignore[import-untyped]

from pos.domain import PosError

from . import style
from .dialogs import (
    AdjustmentDialog,
    SalesDialog,
    SettleDialog,
    fmt,
    run_dialog,
    show_error,
)


class SaleScreen(ctk.CTkFrame):
    """Build and settle sales, manage sold-out, adjustments and corrections."""

    def __init__(self, master, app) -> None:
        super().__init__(master, corner_radius=0)
        self.app = app
        self.session = app.session

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(12, 0))
        ctk.CTkLabel(
            top, text=f"Device: {self.session.device_name()}", font=style.FONT_SUBTITLE
        ).pack(side="left")
        self.summary_var = tk.StringVar()
        ctk.CTkLabel(top, textvariable=self.summary_var).pack(side="left", padx=16)
        ctk.CTkButton(
            top, text="End of day", width=120, command=self.app.show_end_of_day
        ).pack(side="right")
        ctk.CTkButton(
            top, text="Sales", width=90, command=self._open_sales
        ).pack(side="right", padx=4)
        ctk.CTkButton(
            top, text="Cash adjustment", width=150, command=self._open_adjustment
        ).pack(side="right", padx=4)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=8)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        # Left: item list
        left = ctk.CTkFrame(body, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        ctk.CTkLabel(left, text="Items", anchor="w").pack(fill="x")
        self.item_tree = style.make_table(
            left,
            ("item_id", "name", "price", "remaining", "status"),
            ("ID", "Item", "Price", "Remaining", "Status"),
            height=20,
        )
        self.item_tree.pack(fill="both", expand=True, pady=(4, 4))

        controls = ctk.CTkFrame(left, fg_color="transparent")
        controls.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(controls, text="Qty:").pack(side="left")
        self.qty_var = tk.StringVar(value="1")
        ctk.CTkEntry(controls, textvariable=self.qty_var, width=50).pack(side="left")
        ctk.CTkButton(
            controls, text="Add to sale", width=110, command=self._add_to_sale
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            controls, text="Toggle sold-out", width=130, command=self._toggle_sold_out
        ).pack(side="left", padx=4)

        # Right: current sale
        right = ctk.CTkFrame(body, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        ctk.CTkLabel(right, text="Current sale", anchor="w").pack(fill="x")
        self.sale_tree = style.make_table(
            right, ("item", "qty", "total"), ("Item", "Qty", "Total"), height=12
        )
        self.sale_tree.pack(fill="both", expand=True, pady=(4, 4))

        sale_controls = ctk.CTkFrame(right, fg_color="transparent")
        sale_controls.pack(fill="x", pady=(0, 4))
        self.sale_qty_var = tk.StringVar(value="1")
        ctk.CTkEntry(
            sale_controls, textvariable=self.sale_qty_var, width=50
        ).pack(side="left")
        ctk.CTkButton(
            sale_controls, text="Set qty", width=80, command=self._set_qty
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            sale_controls, text="Remove", width=80, command=self._remove_from_sale
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            sale_controls, text="New sale", width=90, command=self._new_sale
        ).pack(side="right")

        self.total_var = tk.StringVar()
        ctk.CTkLabel(
            right,
            textvariable=self.total_var,
            font=style.FONT_TOTAL,
            anchor="e",
        ).pack(fill="x", pady=(4, 0))
        ctk.CTkButton(
            right,
            text="Settle",
            height=40,
            font=style.FONT_BUTTON,
            fg_color=style.SETTLE_COLOR,
            hover_color=style.SETTLE_HOVER,
            command=self._settle,
        ).pack(fill="x", pady=(6, 0))

        self.refresh()

    # -- actions ------------------------------------------------------------

    def refresh(self) -> None:
        self.item_tree.delete(*self.item_tree.get_children())
        for stock in self.session.list_items():
            remaining = "—" if stock.remaining is None else str(stock.remaining)
            status = "sold out" if stock.sold_out else ""
            self.item_tree.insert(
                "",
                "end",
                values=(stock.item_id, stock.name, fmt(stock.price), remaining, status),
                tags=("sold_out",) if stock.sold_out else (),
            )
        style.configure_sold_out_tag(self.item_tree)

        self.sale_tree.delete(*self.sale_tree.get_children())
        for line in self.session.current_sale_items():
            self.sale_tree.insert(
                "",
                "end",
                iid=line.item_id,
                values=(line.item_name, line.quantity, fmt(line.total)),
            )
        self.total_var.set(f"Total: ${fmt(self.session.current_sale_total())}")

        summary = self.session.running_summary()
        self.summary_var.set(
            f"Takings: ${fmt(summary.takings)}   Sales: {summary.sale_count}"
        )

    def reapply_theme(self) -> None:
        style.configure_sold_out_tag(self.item_tree)

    def _selected_item_id(self):
        selection = self.item_tree.selection()
        if not selection:
            return None
        return self.item_tree.item(selection[0], "values")[0]

    def _add_to_sale(self) -> None:
        item_id = self._selected_item_id()
        if item_id is None:
            return
        try:
            self.session.add_item_to_sale(item_id, int(self.qty_var.get()))
        except (PosError, ValueError) as exc:
            show_error("Cannot add item", exc)
        self.refresh()

    def _toggle_sold_out(self) -> None:
        item_id = self._selected_item_id()
        if item_id is None:
            return
        try:
            if self.session.is_sold_out(item_id):
                self.session.unmark_sold_out(item_id)
            else:
                self.session.mark_sold_out(item_id)
        except PosError as exc:
            show_error("Cannot change sold-out", exc)
        self.refresh()

    def _selected_sale_item_id(self):
        selection = self.sale_tree.selection()
        if not selection:
            return None
        return selection[0]

    def _set_qty(self) -> None:
        item_id = self._selected_sale_item_id()
        if item_id is None:
            return
        try:
            self.session.set_sale_quantity(item_id, int(self.sale_qty_var.get()))
        except (PosError, ValueError) as exc:
            show_error("Cannot set quantity", exc)
        self.refresh()

    def _remove_from_sale(self) -> None:
        item_id = self._selected_sale_item_id()
        if item_id is None:
            return
        self.session.set_sale_quantity(item_id, 0)
        self.refresh()

    def _new_sale(self) -> None:
        self.session.begin_sale()
        self.refresh()

    def _settle(self) -> None:
        if not self.session.current_sale_items():
            messagebox.showinfo("No sale", "The current sale is empty.")
            return
        dialog = SettleDialog(self, self.session)
        run_dialog(dialog)
        self.refresh()

    def _open_sales(self) -> None:
        dialog = SalesDialog(self, self.session)
        run_dialog(dialog)
        self.refresh()

    def _open_adjustment(self) -> None:
        dialog = AdjustmentDialog(self, self.session)
        run_dialog(dialog)
        self.refresh()
