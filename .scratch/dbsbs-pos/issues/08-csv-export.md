# 08 — CSV export

**What to build:** Each device exports its sales as two CSV files the organizer can open in a spreadsheet and merge by hand with the other device's. The sales file carries one row per sale (device name, sequence number, timestamps, status, total, and per-tender amounts); the line-items file carries one row per line item (device, sequence number, item, quantity, price). Voided sales appear with a `voided` status so the organizer can filter them out of totals while still seeing them.

**Blocked by:** 04 — Correct & void a sale

**Status:** ready-for-agent

- [ ] The sales export contains one row per sale: device, sequence number, timestamps, status, total, cash amount, Octopus amount, voucher amount
- [ ] The line-items export contains one row per (sale, item): device, sequence number, item, quantity, price
- [ ] Voided sales are present in both exports with a `voided` status, filterable but visible
- [ ] Both files are comma-delimited UTF-8 with a header row, and open cleanly in a spreadsheet
- [ ] Corrected sales appear in their final state with their original creation time
