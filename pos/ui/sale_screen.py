"""UI layer — the sale screen. Untested by design (docs/spec.md)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from pos.domain import PosError

from .dialogs import (
    AdjustmentDialog,
    ItemDialog,
    SalesDialog,
    SettleDialog,
    fmt,
    run_dialog,
    show_error,
)


class SaleScreen(ttk.Frame):
    """Build and settle sales, manage sold-out, adjustments and corrections."""

    def __init__(self, master, app) -> None:
        super().__init__(master, padding=12)
        self.app = app
        self.session = app.session

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(
            top, text=f"Device: {self.session.device_name()}", font=("Segoe UI", 12)
        ).pack(side="left")
        self.summary_var = tk.StringVar()
        ttk.Label(top, textvariable=self.summary_var).pack(side="left", padx=16)
        ttk.Button(top, text="End of day", command=self.app.show_end_of_day).pack(
            side="right"
        )
        ttk.Button(top, text="Sales", command=self._open_sales).pack(side="right", padx=4)
        ttk.Button(top, text="Catalog", command=self._open_catalog).pack(side="right", padx=4)
        ttk.Button(top, text="Cash adjustment", command=self._open_adjustment).pack(
            side="right", padx=4
        )

        body = ttk.PanedWindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, pady=8)

        # Left: item list
        left = ttk.Frame(body)
        body.add(left, weight=3)
        ttk.Label(left, text="Items").pack(anchor="w")
        columns = ("name", "price", "remaining", "status")
        self.item_tree = ttk.Treeview(
            left, columns=columns, show="headings", height=20
        )
        for col, text in zip(columns, ["Item", "Price", "Remaining", "Status"]):
            self.item_tree.heading(col, text=text)
        self.item_tree.pack(fill="both", expand=True)

        controls = ttk.Frame(left)
        controls.pack(fill="x", pady=4)
        ttk.Label(controls, text="Qty:").pack(side="left")
        self.qty_var = tk.StringVar(value="1")
        ttk.Entry(controls, textvariable=self.qty_var, width=4).pack(side="left")
        ttk.Button(controls, text="Add to sale", command=self._add_to_sale).pack(
            side="left", padx=4
        )
        ttk.Button(controls, text="Toggle sold-out", command=self._toggle_sold_out).pack(
            side="left", padx=4
        )

        # Right: current sale
        right = ttk.Frame(body)
        body.add(right, weight=2)
        ttk.Label(right, text="Current sale").pack(anchor="w")
        sale_columns = ("item", "qty", "total")
        self.sale_tree = ttk.Treeview(
            right, columns=sale_columns, show="headings", height=12
        )
        for col, text in zip(sale_columns, ["Item", "Qty", "Total"]):
            self.sale_tree.heading(col, text=text)
        self.sale_tree.pack(fill="both", expand=True)

        sale_controls = ttk.Frame(right)
        sale_controls.pack(fill="x", pady=4)
        self.sale_qty_var = tk.StringVar(value="1")
        ttk.Entry(sale_controls, textvariable=self.sale_qty_var, width=4).pack(
            side="left"
        )
        ttk.Button(sale_controls, text="Set qty", command=self._set_qty).pack(
            side="left", padx=4
        )
        ttk.Button(sale_controls, text="Remove", command=self._remove_from_sale).pack(
            side="left", padx=4
        )
        ttk.Button(sale_controls, text="New sale", command=self._new_sale).pack(
            side="right"
        )

        self.total_var = tk.StringVar()
        ttk.Label(right, textvariable=self.total_var, font=("Segoe UI", 14)).pack(
            anchor="e"
        )
        ttk.Button(right, text="Settle", command=self._settle).pack(fill="x", pady=4)

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
                values=(stock.name, fmt(stock.price), remaining, status),
                tags=("sold_out",) if stock.sold_out else (),
            )
        self.item_tree.tag_configure("sold_out", foreground="#999999")

        self.sale_tree.delete(*self.sale_tree.get_children())
        for line in self.session.current_sale_items():
            self.sale_tree.insert(
                "",
                "end",
                values=(line.item_name, line.quantity, fmt(line.total)),
            )
        self.total_var.set(f"Total: ${fmt(self.session.current_sale_total())}")

        summary = self.session.running_summary()
        self.summary_var.set(
            f"Takings: ${fmt(summary.takings)}   Sales: {summary.sale_count}"
        )

    def _selected_item_name(self):
        selection = self.item_tree.selection()
        if not selection:
            return None
        return self.item_tree.item(selection[0], "values")[0]

    def _add_to_sale(self) -> None:
        name = self._selected_item_name()
        if name is None:
            return
        try:
            self.session.add_item_to_sale(name, int(self.qty_var.get()))
        except (PosError, ValueError) as exc:
            show_error("Cannot add item", exc)
        self.refresh()

    def _toggle_sold_out(self) -> None:
        name = self._selected_item_name()
        if name is None:
            return
        try:
            if self.session.is_sold_out(name):
                self.session.unmark_sold_out(name)
            else:
                self.session.mark_sold_out(name)
        except PosError as exc:
            show_error("Cannot change sold-out", exc)
        self.refresh()

    def _selected_sale_item(self):
        selection = self.sale_tree.selection()
        if not selection:
            return None
        return self.sale_tree.item(selection[0], "values")[0]

    def _set_qty(self) -> None:
        name = self._selected_sale_item()
        if name is None:
            return
        try:
            self.session.set_sale_quantity(name, int(self.sale_qty_var.get()))
        except (PosError, ValueError) as exc:
            show_error("Cannot set quantity", exc)
        self.refresh()

    def _remove_from_sale(self) -> None:
        name = self._selected_sale_item()
        if name is None:
            return
        self.session.set_sale_quantity(name, 0)
        self.refresh()

    def _new_sale(self) -> None:
        self.session.begin_sale()
        self.refresh()

    def _settle(self) -> None:
        if not self.session.current_sale_items():
            from tkinter import messagebox

            messagebox.showinfo("No sale", "The current sale is empty.")
            return
        dialog = SettleDialog(self, self.session)
        run_dialog(dialog)
        self.refresh()

    def _open_sales(self) -> None:
        dialog = SalesDialog(self, self.session)
        run_dialog(dialog)
        self.refresh()

    def _open_catalog(self) -> None:
        dialog = ItemDialog(self, self.session)
        run_dialog(dialog)
        self.refresh()

    def _open_adjustment(self) -> None:
        dialog = AdjustmentDialog(self, self.session)
        run_dialog(dialog)
        self.refresh()
