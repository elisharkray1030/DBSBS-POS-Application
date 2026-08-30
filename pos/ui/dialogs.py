"""UI layer — dialogs shared across screens. Untested by design (docs/spec.md)."""

from __future__ import annotations

import tkinter as tk
from decimal import Decimal
from tkinter import filedialog, messagebox

import customtkinter as ctk  # type: ignore[import-untyped]

from pos import diagnostics
from pos.diagnostics import LogSource
from pos.domain import (
    CASH,
    OCTOPUS,
    VOUCHER,
    LineItem,
    PosError,
    Tender,
    money,
)

from . import style


def fmt(amount: Decimal) -> str:
    return f"{amount:.2f}"


def show_error(title: str, exc: Exception, source: LogSource) -> None:
    messagebox.showerror(title, str(exc))
    diagnostics.log_failure(source, str(exc))


def run_dialog(dialog: ctk.CTkToplevel) -> None:
    if dialog.master is not None:
        dialog.transient(dialog.master)  # type: ignore[call-overload]
    dialog.grab_set()
    dialog.wait_window()


class TenderSection(ctk.CTkFrame):
    """Lets the cashier choose how a sale is settled and builds the tenders.

    The settlement rules live in the facade; this section only assembles the
    tender list the cashier has chosen.
    """

    def __init__(self, master: tk.Misc, total: Decimal) -> None:
        super().__init__(master, corner_radius=8, border_width=1)
        self.total = total
        self.method = tk.StringVar(value=CASH)

        ctk.CTkLabel(self, text="Settlement", font=style.FONT_SUBTITLE).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=8, pady=(8, 4)
        )

        methods = [CASH, VOUCHER, OCTOPUS, "cash+voucher"]
        labels = ["Cash", "Voucher", "Octopus", "Cash + Voucher"]
        for column, (method, label) in enumerate(zip(methods, labels)):
            ctk.CTkRadioButton(
                self,
                text=label,
                value=method,
                variable=self.method,
                command=self._update_fields,
            ).grid(row=1, column=column, sticky="w", padx=8, pady=4)

        self.cash_tendered = ctk.CTkEntry(self, width=110)
        self.cash_portion = ctk.CTkEntry(self, width=110)
        self.voucher_portion = ctk.CTkEntry(self, width=110)
        self._update_fields()

    def set_total(self, total: Decimal) -> None:
        self.total = total

    def _update_fields(self) -> None:
        method = self.method.get()
        self.cash_tendered.grid_remove()
        self.cash_portion.grid_remove()
        self.voucher_portion.grid_remove()
        if method == CASH:
            self._label("Cash tendered (notes given)", 2, 0)
            self.cash_tendered.grid(row=2, column=1, padx=8, pady=4, sticky="w")
        elif method == "cash+voucher":
            self._label("Cash portion", 2, 0)
            self.cash_portion.grid(row=2, column=1, padx=8, pady=4, sticky="w")
            self._label("Cash tendered", 3, 0)
            self.cash_tendered.grid(row=3, column=1, padx=8, pady=4, sticky="w")
            self._label("Voucher portion", 4, 0)
            self.voucher_portion.grid(row=4, column=1, padx=8, pady=4, sticky="w")

    def _label(self, text: str, row: int, column: int) -> None:
        ctk.CTkLabel(self, text=text).grid(
            row=row, column=column, sticky="e", padx=8, pady=4
        )

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


class SettleDialog(ctk.CTkToplevel):
    """Settle the current sale."""

    def __init__(self, master: tk.Misc, session) -> None:
        super().__init__(master)
        self.session = session
        self.title("Settle sale")
        total = session.current_sale_total()
        ctk.CTkLabel(
            self, text=f"Sale total: ${fmt(total)}", font=style.FONT_HEADING
        ).pack(padx=12, pady=(12, 8))
        self.section = TenderSection(self, total)
        self.section.pack(fill="x", padx=12, pady=4)
        ctk.CTkButton(self, text="Settle", command=self._settle).pack(
            padx=12, pady=10
        )

    def _settle(self) -> None:
        try:
            result = self.session.settle_current_sale(self.section.build_tenders())
        except PosError as exc:
            show_error("Cannot settle", exc, LogSource.SETTLEMENT)
            return
        messagebox.showinfo(
            "Sale settled",
            f"Sale #{result.seq}\nChange due: ${fmt(result.change_due)}",
        )
        self.destroy()


class AdjustmentDialog(ctk.CTkToplevel):
    """Record cash added to or removed from the till."""

    def __init__(self, master: tk.Misc, session) -> None:
        super().__init__(master)
        self.session = session
        self.title("Cash adjustment")
        ctk.CTkLabel(
            self,
            text="Amount (positive = added, negative = removed)",
        ).grid(row=0, column=0, columnspan=2, padx=12, pady=(12, 4))
        ctk.CTkLabel(self, text="Amount:").grid(row=1, column=0, sticky="e", padx=8)
        self.amount = ctk.CTkEntry(self, width=140)
        self.amount.grid(row=1, column=1, padx=8, pady=4)
        ctk.CTkLabel(self, text="Reason:").grid(row=2, column=0, sticky="e", padx=8)
        self.reason = ctk.CTkEntry(self, width=280)
        self.reason.grid(row=2, column=1, padx=8, pady=4)
        ctk.CTkButton(self, text="Record", command=self._record).grid(
            row=3, column=0, columnspan=2, pady=10
        )

    def _record(self) -> None:
        try:
            amount = money(self.amount.get())
            self.session.record_cash_adjustment(amount, self.reason.get())
        except PosError as exc:
            show_error("Cannot record adjustment", exc, LogSource.CASH_ADJUSTMENT)
            return
        self.destroy()


class SalesDialog(ctk.CTkToplevel):
    """List recorded sales for correction or voiding."""

    def __init__(self, master: tk.Misc, session) -> None:
        super().__init__(master)
        self.session = session
        self.title("Recorded sales")
        ctk.CTkLabel(
            self,
            text="Select a sale, then correct it in place or void it.",
        ).pack(padx=12, pady=(12, 8))

        self.tree = style.make_table(
            self,
            ("seq", "time", "status", "total"),
            ("Seq", "Time", "Status", "Total"),
            height=12,
        )
        self.tree.pack(fill="both", expand=True, padx=12)

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(pady=10)
        ctk.CTkButton(buttons, text="Correct...", command=self._correct).pack(
            side="left", padx=4
        )
        ctk.CTkButton(buttons, text="Void", command=self._void).pack(side="left", padx=4)
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
            show_error("Cannot void", exc, LogSource.VOID)
        self._refresh()


class CorrectionDialog(ctk.CTkToplevel):
    """Edit a recorded sale in place: change quantities, add or remove lines,
    and re-settle it."""

    def __init__(self, master: tk.Misc, session, seq: int) -> None:
        super().__init__(master)
        self.session = session
        self.seq = seq
        self.title(f"Correct sale #{seq}")
        sale = session.get_sale(seq)

        ctk.CTkLabel(
            self,
            text=f"Sale #{seq} — edit the items and settlement, then save.",
        ).pack(padx=12, pady=(12, 8))

        self.lines: list[LineItem] = list(sale.line_items)
        self.row_vars: list[tuple[LineItem, tk.StringVar]] = []

        self.rows = ctk.CTkFrame(self, fg_color="transparent")
        self.rows.pack(fill="both", expand=True, padx=12)

        add_row = ctk.CTkFrame(self, fg_color="transparent")
        add_row.pack(fill="x", padx=12, pady=(4, 0))
        self._combo_items = {
            f"{i.item_id} — {i.name}": i for i in session.list_items()
        }
        self.item_combo = ctk.CTkComboBox(
            add_row,
            values=list(self._combo_items),
            width=220,
        )
        self.item_combo.pack(side="left")
        self.add_qty = ctk.CTkEntry(add_row, width=50)
        self.add_qty.insert(0, "1")
        self.add_qty.pack(side="left", padx=4)
        ctk.CTkButton(add_row, text="Add line", command=self._add_line).pack(
            side="left", padx=4
        )

        self.total_var = tk.StringVar()
        ctk.CTkLabel(self, textvariable=self.total_var, font=style.FONT_HEADING).pack(
            anchor="e", padx=12, pady=(4, 0)
        )

        self.section = TenderSection(self, sale.total)
        self.section.pack(fill="x", padx=12, pady=4)
        ctk.CTkButton(self, text="Save correction", command=self._save).pack(
            padx=12, pady=10
        )

        self._rebuild_rows()

    # -- line editing -------------------------------------------------------

    def _rebuild_rows(self) -> None:
        for child in self.rows.winfo_children():
            child.destroy()
        self.row_vars = []
        for line in self.lines:
            var = tk.StringVar(value=str(line.quantity))
            var.trace_add("write", lambda *_: self._recompute_total())
            row = ctk.CTkFrame(self.rows, fg_color="transparent")
            row.pack(fill="x")
            ctk.CTkLabel(row, text=line.item_name, width=180, anchor="w").pack(
                side="left"
            )
            ctk.CTkLabel(row, text=f"${fmt(line.price)}", width=90).pack(side="left")
            ctk.CTkEntry(row, textvariable=var, width=60).pack(side="left", padx=4)
            ctk.CTkButton(
                row,
                text="Remove",
                width=80,
                command=lambda item_id=line.item_id: self._remove_line(item_id),  # type: ignore[misc]
            ).pack(side="right", padx=4)
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
            show_error("Cannot correct", exc, LogSource.CORRECTION)
            return
        self.destroy()


class ExportDialog(ctk.CTkToplevel):
    """Export the device's sales as CSV files."""

    def __init__(self, master: tk.Misc, session) -> None:
        super().__init__(master)
        self.session = session
        self.title("Export CSV")
        ctk.CTkLabel(
            self,
            text="Choose a folder for sales.csv, items.csv, and the\n"
            "device's Stock sheet report.",
        ).pack(padx=12, pady=(12, 8))
        self.folder = tk.StringVar()
        ctk.CTkEntry(self, textvariable=self.folder, width=360).pack(padx=12)
        ctk.CTkButton(self, text="Browse...", command=self._browse).pack(
            padx=12, pady=6
        )
        ctk.CTkButton(self, text="Export", command=self._export).pack(
            padx=12, pady=(0, 12)
        )

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
            show_error("Cannot export", exc, LogSource.EXPORT)
            return
        messagebox.showinfo(
            "Export complete",
            "Wrote:\n" + "\n".join(str(p) for p in paths),
        )
        self.destroy()


class WipeDialog(ctk.CTkToplevel):
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
        ctk.CTkLabel(
            self,
            text="This permanently deletes all sales, the catalog, adjustments,\n"
            "and settings from this device. You must export first.\n"
            "Type the word 'wipe' to confirm.",
        ).pack(padx=16, pady=(12, 8))
        self.entry = ctk.CTkEntry(self, width=160)
        self.entry.pack(padx=12)
        ctk.CTkButton(self, text="Wipe database", command=self._wipe).pack(
            padx=12, pady=12
        )

    def _wipe(self) -> None:
        if self.entry.get().strip().lower() != "wipe":
            messagebox.showwarning("Not confirmed", "Type 'wipe' to confirm.")
            return
        try:
            self.session.wipe()
        except PosError as exc:
            show_error("Cannot wipe", exc, LogSource.WIPE)
            return
        self.destroy()
        self.on_wipe()
