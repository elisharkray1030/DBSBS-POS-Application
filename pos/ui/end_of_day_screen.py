"""UI layer — the end-of-day screen. Untested by design (docs/spec.md)."""

from __future__ import annotations

from tkinter import ttk

from .dialogs import ExportDialog, WipeDialog, fmt, run_dialog


class EndOfDayScreen(ttk.Frame):
    """Per-device reconciliation figures for the organizer."""

    def __init__(self, master, app) -> None:
        super().__init__(master, padding=12)
        self.app = app
        self.session = app.session

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(
            top, text=f"End of day — {self.session.device_name()}", font=("Segoe UI", 14)
        ).pack(side="left")
        ttk.Button(top, text="Back to sales", command=self.app.show_sale).pack(
            side="right"
        )

        figures = self.session.end_of_day()

        summary = ttk.Frame(self)
        summary.pack(fill="x", pady=8)
        ttk.Label(
            summary, text=f"Expected cash: ${fmt(figures.expected_cash)}", font=("Segoe UI", 12)
        ).pack(anchor="w")
        ttk.Label(summary, text=f"Octopus: ${fmt(figures.octopus_total)}").pack(anchor="w")
        ttk.Label(summary, text=f"Vouchers: ${fmt(figures.voucher_total)}").pack(anchor="w")

        ttk.Label(self, text="Items sold (this device, excluding voids)").pack(anchor="w")
        sold = ttk.Treeview(self, columns=("item", "count"), show="headings", height=8)
        sold.heading("item", text="Item")
        sold.heading("count", text="Sold")
        sold.pack(fill="x", pady=(2, 6))
        name_by_id = {i.item_id: i.name for i in self.session.list_items()}
        for item_id, count in figures.sold_counts.items():
            sold.insert("", "end", values=(name_by_id.get(item_id, item_id), count))

        ttk.Label(self, text="Voids").pack(anchor="w")
        voids = ttk.Treeview(self, columns=("seq", "time", "total"), show="headings", height=5)
        for col, text in zip(("seq", "time", "total"), ["Seq", "Time", "Total"]):
            voids.heading(col, text=text)
        voids.pack(fill="x", pady=(2, 6))
        for sale in figures.voids:
            voids.insert(
                "",
                "end",
                values=(sale.seq, sale.created_at.strftime("%H:%M"), fmt(sale.total)),
            )

        ttk.Label(self, text="Cash adjustments").pack(anchor="w")
        adjustments = ttk.Treeview(
            self, columns=("amount", "reason", "time"), show="headings", height=4
        )
        for col, text in zip(
            ("amount", "reason", "time"), ["Amount", "Reason", "Time"]
        ):
            adjustments.heading(col, text=text)
        adjustments.pack(fill="x", pady=(2, 6))
        for adjustment in figures.cash_adjustments:
            adjustments.insert(
                "",
                "end",
                values=(
                    fmt(adjustment.amount),
                    adjustment.reason,
                    adjustment.created_at.strftime("%H:%M"),
                ),
            )

        buttons = ttk.Frame(self)
        buttons.pack(pady=8)
        ttk.Button(buttons, text="Export CSV", command=self._export).pack(side="left", padx=4)
        ttk.Button(buttons, text="Wipe for end of event", command=self._wipe).pack(
            side="left", padx=4
        )

    def _export(self) -> None:
        dialog = ExportDialog(self, self.session)
        run_dialog(dialog)

    def _wipe(self) -> None:
        dialog = WipeDialog(self, self.session, self.app.show_setup)
        run_dialog(dialog)
