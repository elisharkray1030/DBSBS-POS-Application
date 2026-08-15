"""UI layer — dialogs shared across screens. Untested by design (docs/spec.md)."""

from __future__ import annotations

import tkinter as tk
from decimal import Decimal
from tkinter import filedialog, messagebox, ttk

from pos.domain import (
    CASH,
    OCTOPUS,
    VOUCHER,
    LineItem,
    PosError,
    Tender,
    money,
)


def fmt(amount: Decimal) -> str:
    return f"{amount:.2f}"


def show_error(title: str, exc: Exception) -> None:
    messagebox.showerror(title, str(exc))


def run_dialog(dialog: tk.Toplevel) -> None:
    if dialog.master is not None:
        dialog.transient(dialog.master)  # type: ignore[call-overload]
    dialog.grab_set()
    dialog.wait_window()


class TenderSection(ttk.LabelFrame):
    """Lets the cashier choose how a sale is settled and builds the tenders.

    The settlement rules live in the facade; this section only assembles the
    tender list the cashier has chosen.
    """

    def __init__(self, master: tk.Misc, total: Decimal) -> None:
        super().__init__(master, text="Settlement")
        self.total = total
        self.method = tk.StringVar(value=CASH)

        methods = [CASH, VOUCHER, OCTOPUS, "cash+voucher"]
        labels = ["Cash", "Voucher", "Octopus", "Cash + Voucher"]
        for column, (method, label) in enumerate(zip(methods, labels)):
            ttk.Radiobutton(
                self,
                text=label,
                value=method,
                variable=self.method,
                command=self._update_fields,
            ).grid(row=0, column=column, sticky="w", padx=4, pady=4)

        self.cash_tendered = ttk.Entry(self, width=10)
        self.cash_portion = ttk.Entry(self, width=10)
        self.voucher_portion = ttk.Entry(self, width=10)
        self._update_fields()

    def set_total(self, total: Decimal) -> None:
        self.total = total

    def _update_fields(self) -> None:
        method = self.method.get()
        self.cash_tendered.grid_remove()
        self.cash_portion.grid_remove()
        self.voucher_portion.grid_remove()
        if method == CASH:
            self._label("Cash tendered (notes given)", 1, 0)
            self.cash_tendered.grid(row=1, column=1, padx=4, pady=4)
        elif method == "cash+voucher":
            self._label("Cash portion", 1, 0)
            self.cash_portion.grid(row=1, column=1, padx=4, pady=4)
            self._label("Cash tendered", 2, 0)
            self.cash_tendered.grid(row=2, column=1, padx=4, pady=4)
            self._label("Voucher portion", 3, 0)
            self.voucher_portion.grid(row=3, column=1, padx=4, pady=4)

    def _label(self, text: str, row: int, column: int) -> None:
        ttk.Label(self, text=text).grid(row=row, column=column, sticky="e", padx=4)

    def build_tenders(self) -> list[Tender]:
        method = self.method.get()
        if method == CASH:
            return [
                Tender(CASH, self.total, tendered=money(self.cash_tendered.get()))
            ]
        if method == VOUCHER:
            return [Tender(VOUCHER, self.total)]
        if method == OCTOPUS:
            return [Tender(OCTOPUS, self.total)]
        cash = money(self.cash_portion.get())
        voucher = money(self.voucher_portion.get())
        return [
            Tender(CASH, cash, tendered=money(self.cash_tendered.get())),
            Tender(VOUCHER, voucher),
        ]


class SettleDialog(tk.Toplevel):
    """Settle the current sale."""

    def __init__(self, master: tk.Misc, session) -> None:
        super().__init__(master)
        self.session = session
        self.title("Settle sale")
        total = session.current_sale_total()
        ttk.Label(self, text=f"Sale total: ${fmt(total)}").pack(padx=12, pady=(12, 4))
        self.section = TenderSection(self, total)
        self.section.pack(fill="x", padx=12, pady=4)
        ttk.Button(self, text="Settle", command=self._settle).pack(pady=8)

    def _settle(self) -> None:
        try:
            result = self.session.settle_current_sale(self.section.build_tenders())
        except PosError as exc:
            show_error("Cannot settle", exc)
            return
        messagebox.showinfo(
            "Sale settled",
            f"Sale #{result.seq}\nChange due: ${fmt(result.change_due)}",
        )
        self.destroy()


class AdjustmentDialog(tk.Toplevel):
    """Record cash added to or removed from the till."""

    def __init__(self, master: tk.Misc, session) -> None:
        super().__init__(master)
        self.session = session
        self.title("Cash adjustment")
        ttk.Label(
            self,
            text="Amount (positive = added, negative = removed)",
        ).grid(row=0, column=0, columnspan=2, padx=12, pady=(12, 4))
        ttk.Label(self, text="Amount:").grid(row=1, column=0, sticky="e", padx=4)
        self.amount = ttk.Entry(self, width=12)
        self.amount.grid(row=1, column=1, padx=4, pady=4)
        ttk.Label(self, text="Reason:").grid(row=2, column=0, sticky="e", padx=4)
        self.reason = ttk.Entry(self, width=28)
        self.reason.grid(row=2, column=1, padx=4, pady=4)
        ttk.Button(self, text="Record", command=self._record).grid(
            row=3, column=0, columnspan=2, pady=8
        )

    def _record(self) -> None:
        try:
            amount = money(self.amount.get())
            self.session.record_cash_adjustment(amount, self.reason.get())
        except PosError as exc:
            show_error("Cannot record adjustment", exc)
            return
        self.destroy()


class SalesDialog(tk.Toplevel):
    """List recorded sales for correction or voiding."""

    def __init__(self, master: tk.Misc, session) -> None:
        super().__init__(master)
        self.session = session
        self.title("Recorded sales")
        ttk.Label(
            self,
            text="Select a sale, then correct it in place or void it.",
        ).pack(padx=12, pady=(12, 4))

        columns = ("seq", "time", "status", "total")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=12)
        for col, text in zip(columns, ["Seq", "Time", "Status", "Total"]):
            self.tree.heading(col, text=text)
        self.tree.pack(fill="both", expand=True, padx=12)

        buttons = ttk.Frame(self)
        buttons.pack(pady=8)
        ttk.Button(buttons, text="Correct...", command=self._correct).pack(
            side="left", padx=4
        )
        ttk.Button(buttons, text="Void", command=self._void).pack(side="left", padx=4)
        self._refresh()

    def _refresh(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for sale in self.session.list_sales():
            self.tree.insert(
                "",
                "end",
                values=(
                    sale.seq,
                    sale.created_at.strftime("%H:%M"),
                    sale.status,
                    fmt(sale.total),
                ),
            )

    def _selected_seq(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("No selection", "Select a sale first.")
            return None
        return int(self.tree.item(selection[0], "values")[0])

    def _correct(self) -> None:
        seq = self._selected_seq()
        if seq is None:
            return
        dialog = CorrectionDialog(self, self.session, seq)
        run_dialog(dialog)
        self._refresh()

    def _void(self) -> None:
        seq = self._selected_seq()
        if seq is None:
            return
        if not messagebox.askyesno("Void sale", f"Void sale #{seq}?"):
            return
        try:
            self.session.void_sale(seq)
        except PosError as exc:
            show_error("Cannot void", exc)
        self._refresh()


class CorrectionDialog(tk.Toplevel):
    """Edit a recorded sale in place: change quantities, add or remove lines,
    and re-settle it."""

    def __init__(self, master: tk.Misc, session, seq: int) -> None:
        super().__init__(master)
        self.session = session
        self.seq = seq
        self.title(f"Correct sale #{seq}")
        sale = session.get_sale(seq)

        ttk.Label(
            self,
            text=f"Sale #{seq} — edit the items and settlement, then save.",
        ).pack(padx=12, pady=(12, 4))

        self.lines: list[LineItem] = list(sale.line_items)
        self.row_vars: list[tuple[LineItem, tk.StringVar]] = []

        self.rows = ttk.Frame(self)
        self.rows.pack(fill="both", expand=True, padx=12)

        add_row = ttk.Frame(self)
        add_row.pack(fill="x", padx=12, pady=(4, 0))
        self._combo_items = {
            f"{i.item_id} — {i.name}": i for i in session.list_items()
        }
        self.item_combo = ttk.Combobox(
            add_row,
            values=list(self._combo_items),
            width=16,
        )
        self.item_combo.pack(side="left")
        self.add_qty = ttk.Entry(add_row, width=4)
        self.add_qty.insert(0, "1")
        self.add_qty.pack(side="left", padx=4)
        ttk.Button(add_row, text="Add line", command=self._add_line).pack(side="left")

        self.total_var = tk.StringVar()
        ttk.Label(self, textvariable=self.total_var, font=("Segoe UI", 13)).pack(
            anchor="e", padx=12, pady=(4, 0)
        )

        self.section = TenderSection(self, sale.total)
        self.section.pack(fill="x", padx=12, pady=4)
        ttk.Button(self, text="Save correction", command=self._save).pack(pady=8)

        self._rebuild_rows()

    # -- line editing -------------------------------------------------------

    def _rebuild_rows(self) -> None:
        for child in self.rows.winfo_children():
            child.destroy()
        self.row_vars = []
        for line in self.lines:
            var = tk.StringVar(value=str(line.quantity))
            var.trace_add("write", lambda *_: self._recompute_total())
            row = ttk.Frame(self.rows)
            row.pack(fill="x")
            ttk.Label(row, text=line.item_name, width=18, anchor="w").pack(side="left")
            ttk.Label(row, text=f"${fmt(line.price)}", width=8).pack(side="left")
            ttk.Entry(row, textvariable=var, width=5).pack(side="left", padx=4)
            ttk.Button(
                row,
                text="Remove",
                command=lambda item_id=line.item_id: self._remove_line(item_id),  # type: ignore[misc]
            ).pack(side="right")
            self.row_vars.append((line, var))
        self._recompute_total()

    def _current_total(self) -> Decimal:
        total = Decimal("0")
        for line, var in self.row_vars:
            try:
                qty = int(var.get())
            except ValueError:
                qty = 0
            total += LineItem(line.item_id, line.item_name, max(qty, 0), line.price).total
        return total

    def _recompute_total(self) -> None:
        total = self._current_total()
        self.total_var.set(f"Total: ${fmt(total)}")
        self.section.set_total(total)

    def _add_line(self) -> None:
        item = self._combo_items.get(self.item_combo.get())
        if item is None:
            return
        try:
            quantity = int(self.add_qty.get())
        except ValueError:
            quantity = 1
        if quantity <= 0:
            return
        for line in self.lines:
            if line.item_id == item.item_id:
                line.quantity += quantity
                self._rebuild_rows()
                return
        self.lines.append(LineItem(item.item_id, item.name, quantity, item.price))
        self._rebuild_rows()

    def _remove_line(self, item_id: str) -> None:
        self.lines = [line for line in self.lines if line.item_id != item_id]
        self._rebuild_rows()

    def _save(self) -> None:
        try:
            line_items = [
                LineItem(line.item_id, line.item_name, int(var.get()), line.price)
                for line, var in self.row_vars
            ]
            self.session.correct_sale(
                self.seq, line_items, self.section.build_tenders()
            )
        except (PosError, ValueError) as exc:
            show_error("Cannot correct", exc)
            return
        self.destroy()


class ExportDialog(tk.Toplevel):
    """Export the device's sales as CSV files."""

    def __init__(self, master: tk.Misc, session) -> None:
        super().__init__(master)
        self.session = session
        self.title("Export CSV")
        ttk.Label(
            self,
            text="Choose a folder for sales.csv, items.csv, and the\n"
            "device's Stock sheet report.",
        ).pack(padx=12, pady=(12, 4))
        self.folder = tk.StringVar()
        ttk.Entry(self, textvariable=self.folder, width=40).pack(padx=12)
        ttk.Button(self, text="Browse...", command=self._browse).pack(pady=4)
        ttk.Button(self, text="Export", command=self._export).pack(pady=(0, 8))

    def _browse(self) -> None:
        chosen = filedialog.askdirectory(parent=self)
        if chosen:
            self.folder.set(chosen)

    def _export(self) -> None:
        folder = self.folder.get()
        if not folder:
            messagebox.showinfo("No folder", "Choose a folder first.")
            return
        try:
            paths = self.session.export_csv(folder)
        except PosError as exc:
            show_error("Cannot export", exc)
            return
        messagebox.showinfo(
            "Export complete",
            "Wrote:\n" + "\n".join(str(p) for p in paths),
        )
        self.destroy()


class WipeDialog(tk.Toplevel):
    """Wipe the local database for the end of the event.

    The facade blocks the wipe until the end-of-day export has been taken.
    This dialog adds a second, human-level guard: the cashier must type the
    word `wipe` to confirm, so it cannot be triggered accidentally.
    """

    def __init__(self, master: tk.Misc, session, on_wipe) -> None:
        super().__init__(master)
        self.session = session
        self.on_wipe = on_wipe
        self.title("Wipe for end of event")
        ttk.Label(
            self,
            text="This permanently deletes all sales, the catalog, adjustments,\n"
            "and settings from this device. You must export first.\n"
            "Type the word 'wipe' to confirm.",
        ).pack(padx=16, pady=(12, 6))
        self.entry = ttk.Entry(self, width=20)
        self.entry.pack(padx=12)
        ttk.Button(self, text="Wipe database", command=self._wipe).pack(pady=8)

    def _wipe(self) -> None:
        if self.entry.get().strip().lower() != "wipe":
            messagebox.showwarning("Not confirmed", "Type 'wipe' to confirm.")
            return
        try:
            self.session.wipe()
        except PosError as exc:
            show_error("Cannot wipe", exc)
            return
        self.destroy()
        self.on_wipe()
