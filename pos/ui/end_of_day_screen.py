"""UI layer — the end-of-day screen. Untested by design (docs/spec.md)."""

from __future__ import annotations

import customtkinter as ctk  # type: ignore[import-untyped]

from . import style
from .dialogs import ExportDialog, WipeDialog, fmt, run_dialog


class EndOfDayScreen(ctk.CTkFrame):
    """Per-device reconciliation figures for the organizer."""

    def __init__(self, master, app) -> None:
        super().__init__(master, corner_radius=0)
        self.app = app
        self.session = app.session

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(12, 0))
        ctk.CTkLabel(
            top,
            text=f"End of day — {self.session.device_name()}",
            font=style.FONT_HEADING,
        ).pack(side="left")
        ctk.CTkButton(
            top, text="Back to sales", width=120, command=self.app.show_sale
        ).pack(side="right")

        figures = self.session.end_of_day()

        self._section(self, "Cash").pack(fill="x", padx=16, pady=(12, 4))
        summary = ctk.CTkFrame(self, corner_radius=8, border_width=1)
        summary.pack(fill="x", padx=16)
        ctk.CTkLabel(
            summary,
            text=f"Expected cash: ${fmt(figures.expected_cash)}",
            font=("Segoe UI", 16, "bold"),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(8, 2))
        ctk.CTkLabel(
            summary, text=f"Octopus: ${fmt(figures.octopus_total)}", anchor="w"
        ).pack(fill="x", padx=12)
        ctk.CTkLabel(
            summary, text=f"Vouchers: ${fmt(figures.voucher_total)}", anchor="w"
        ).pack(fill="x", padx=12, pady=(2, 8))

        self._section(self, "Items sold (this device, excluding voids)").pack(
            fill="x", padx=16, pady=(12, 2)
        )
        sold = style.make_table(
            self, ("item", "count"), ("Item", "Sold"), height=5
        )
        sold.pack(fill="x", padx=16, pady=(0, 6))
        for row in figures.sold_rows:
            sold.insert("", "end", values=(row.item_name, row.count))

        self._section(self, "Voids").pack(fill="x", padx=16, pady=(4, 2))
        voids = style.make_table(
            self, ("seq", "time", "total"), ("Seq", "Time", "Total"), height=3
        )
        voids.pack(fill="x", padx=16, pady=(0, 6))
        for sale in figures.voids:
            voids.insert(
                "",
                "end",
                values=(sale.seq, sale.created_at.strftime("%H:%M"), fmt(sale.total)),
            )

        self._section(self, "Cash adjustments").pack(fill="x", padx=16, pady=(4, 2))
        adjustments = style.make_table(
            self, ("amount", "reason", "time"), ("Amount", "Reason", "Time"), height=3
        )
        adjustments.pack(fill="x", padx=16, pady=(0, 6))
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

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(pady=8)
        ctk.CTkButton(buttons, text="Export CSV", width=130, command=self._export).pack(
            side="left", padx=4
        )
        ctk.CTkButton(
            buttons,
            text="Wipe for end of event",
            width=180,
            fg_color=style.WIPE_COLOR,
            hover_color=style.WIPE_HOVER,
            command=self._wipe,
        ).pack(side="left", padx=4)

    def _section(self, master, text: str) -> ctk.CTkLabel:
        return ctk.CTkLabel(master, text=text, font=style.FONT_SECTION, anchor="w")

    def _export(self) -> None:
        dialog = ExportDialog(self, self.session)
        run_dialog(dialog)

    def _wipe(self) -> None:
        dialog = WipeDialog(self, self.session, self.app.show_setup)
        run_dialog(dialog)
