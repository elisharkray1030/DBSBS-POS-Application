# 07 — End-of-day view

**What to build:** A per-device end-of-day screen the cashier uses to reconcile against the physical till, the Octopus machine's own report, and the leftover stock. It shows expected cash (float + cash sales + cash added − cash removed), total Octopus taken, total voucher value received, per-item sold counts, and the voids list. Cross-device checks (combining both laptops) are done by the organizer by hand, never by the app.

**Blocked by:** 04 — Correct & void a sale, 06 — Cash adjustments + running summary

**Status:** ready-for-agent

- [ ] The screen shows expected cash for this device: float + cash sales + cash added − cash removed
- [ ] The screen shows total Octopus taken on this device
- [ ] The screen shows total voucher value received on this device
- [ ] The screen shows per-item sold counts for this device, excluding voids
- [ ] The screen shows the voids list
- [ ] All figures are per-device; nothing attempts to combine the other laptop's data
