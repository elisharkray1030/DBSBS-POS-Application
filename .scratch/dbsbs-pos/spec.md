# Spec: DBS Garden Fete POS (single-stall offline register)

> Canonical spec. Lives in `.scratch/dbsbs-pos/spec.md` so the tracker skills
> find it alongside the tickets; visible on GitHub via the repo.

## Problem Statement

The DBS Garden Fete is a one-day annual event held by a boarding school. One particular stall at the fete sells 30–40 DBS-themed physical items over the counter, runs two Windows laptops as tills with one cashier each, and has no reliable network on the day. Today there is no purpose-built register: cashiers hand-write receipts and tally sales by hand, and reconciling the till, the shared Octopus machine, and leftover stock at the end of the day is slow and error-prone. The stall needs a simple, fully-offline point-of-sale application that records every sale, computes totals and change, tracks how many of each item remain, and produces end-of-day figures each device can hand to the organizer.

## Solution

A native desktop POS application, double-clickable on Windows, running fully offline with no browser and no setup beyond copying the folder. One app instance runs on each of the stall's two laptops. Before the event, each device loads the catalog from a CSV (`Name, Price, Quantity`) and records its starting float; the cashier also names the device (e.g. "Till A") so its exports can be told apart. During the event, the cashier builds a sale from a scrollable list of items, the app shows the running total and remaining counts (dimming sold-out items), and the cashier settles the sale by **cash**, **voucher**, or **Octopus** — with cash and vouchers allowed to split across one sale but Octopus always paying the full amount. The app computes cash change, assigns a sequence number and timestamp, and writes the completed sale to a local database file the instant it's made. Cashiers can edit a recorded sale in place (a *correction*, which counts toward totals) or void it (a *void*, which does not count toward totals but is kept in a separate audit section of the export). Mid-day cash top-ups and removals are tracked so expected cash stays accurate. At the end of the day each device exports a CSV of its sales (two files: one row per sale, plus one row per line item), and a summary screen shows expected cash (float + cash sales + adjustments) to compare against the counted till, plus per-item sold counts to compare against the Octopus machine's own report. The organizer combines the two devices' exports by hand in a spreadsheet; the app never merges devices. At the end of the event the local database is wiped so next year starts fresh.

## User Stories

1. As the stall's organizer, I want each laptop to load items from a CSV file before the event, so that the catalog matches the items we'll actually have on the day.
2. As the stall's organizer, I want the CSV to use `Name, Price, Quantity` columns, so that the item list, fixed prices, and starting quantities are all set from one file.
3. As the stall's organizer, I want to give each laptop a short device name at setup (e.g. "Till A"), so that the two devices' exports can be told apart when I merge them later.
4. As the stall's organizer, I want to record the starting float on each laptop, so that the day's takings are separated from the change money in the till.
5. As the cashier, I want to start the day from a simple "load CSV + enter float + name device" setup screen, so that I don't need any technical knowledge to get going.
6. As the cashier, I want to see the items in a scrollable list, so that I can find any of the 30–40 items without hunting.
7. As the cashier, I want to add an item to the current sale with a quantity, so that I can build up a customer's purchase.
8. As the cashier, I want the app to show the running total as I build the sale, so that I can tell the customer what they owe before they pay.
9. As the cashier, I want the list to show how many of each item remain, so that I know what I can still sell.
10. As the cashier, I want sold-out items to be dimmed, so that I don't accidentally try to sell something we've run out of.
11. As the cashier, I want to settle a sale in cash, by voucher, or by Octopus, so that customers can pay however they have.
12. As the cashier, I want to split a sale across cash and vouchers (e.g. $20 cash + $30 voucher), so that a customer can combine their means of payment.
13. As the cashier, I want Octopus to always settle the full sale amount on its own, so that the app's Octopus record matches the single tap on the machine.
14. As the cashier, I want the app to compute the change due when the customer pays cash with a larger note, so that I give back the right amount.
15. As the cashier, I want the app to assign each sale a sequence number and timestamp, so that the handwritten receipt, our records, and the Octopus machine's report can be cross-checked.
16. As the cashier, I want each completed sale written to disk immediately, so that a crash or power loss never loses a finished sale.
17. As the cashier, I want to write the customer's receipt by hand, so that the app stay simple and never needs a printer.
18. As the cashier, I want to edit a just-made sale in place to fix what's wrong (a *correction*), so that the totals reflect what really happened.
19. As the cashier, I want corrections to count toward the day's totals, so that the end-of-day figures are accurate.
20. As the cashier, I want to void a sale to remove it entirely (a *void*), so that a mistaken or cancelled sale doesn't inflate takings.
21. As the cashier, I want voids to not count toward the day's totals, so that takings reflect only real sales.
22. As the cashier, I want voided sales to remain visible in a separate voids section of the export, so that the organizer can see how many were voided and spot anything unusual.
23. As the cashier, I want to record cash added to the till mid-day (e.g. topping up change), so that the end-of-day expected cash still matches the counted till.
24. As the cashier, I want to record cash removed from the till mid-day, so that the end-of-day expected cash still matches the counted till.
25. As the cashier, I want to see a small running summary of today's takings and sale count on the sale screen, so that I can glance at how the day's going without leaving the register.
26. As the cashier, I want to manually mark an item sold-out on my device when I run out, so that I stop offering it even if the other laptop has no network to tell me.
27. As the cashier, I want an end-of-day summary screen showing expected cash (float + cash sales + cash added − cash removed) for this device, so that I can compare it against the cash I physically count in the till.
28. As the cashier, I want the end-of-day summary to show per-item sold counts for this device, so that I can compare against what's left on the table and the organizer can combine both devices.
29. As the cashier, I want the end-of-day summary to show the Octopus total for this device, so that the organizer can combine both devices and compare against the single Octopus machine's report.
30. As the cashier, I want the end-of-day summary to show the voucher total received for this device, so that the vouchers I collected can be reconciled.
31. As the organizer, I want each device to export its sales as CSV (two files: one row per sale, plus one row per line item), so that I can open both devices' exports in a spreadsheet and merge.
32. As the organizer, I want every exported row to carry the device name, so that I can tell Till A's sales from Till B's when combined.
33. As the organizer, I want the sales CSV to carry per-sale fields (sequence number, time, total, cash amount, Octopus amount, voucher amount), so that I can pivot totals per payment type across both devices.
34. As the organizer, I want the line-items CSV to carry one row per (sale, item) with quantity and price, so that I can pivot total sold per item across both devices.
35. As the organizer, I want the export to keep voided sales in a separate section, so I can audit how many sales were voided without them inflating takings.
36. As the organizer, I want to combine the two devices' exports by hand in a spreadsheet, so that I'm never dependent on the app cross-device doing something it can't verify.
37. As the organizer, I want the app to never attempt to sync or merge the two laptops, so that a single device failure never corrupts the other's data.
38. As the organizer, I want the local database to be wiped at the end of the event, so that next year's event starts from a clean slate.
39. As the organizer, I want the app to run double-clickable on Windows with no installer or internet, so that anyone at the stall can launch it.
40. As the organizer, I want the app's entire interface and exports to be in English, so that the team can read everything.
41. As the organizer, I want prices to be whole Hong Kong dollars, so that change-making and the till stay simple (the app should still safely handle cents if they appear).
42. As the cashier, I want last-minute in-app catalog edits to be allowed (add an item, fix a price), so that the CSV isn't a straitjacket if something changes on the day.
43. As the stall's organizer, I want all sales to be final with no refund flow, so that the register stays simple (voiding the original sale is the only correction path).

## Implementation Decisions

- **Platform**: Native-feeling desktop app for Windows, double-clickable, no browser, no installer beyond copying the folder. No network at any point.
- **Persistence**: A single local SQLite database file on each laptop. Every completed sale (and every correction/void/adjustment) is written to disk in its own transaction the moment it is made, so a crash never loses a completed sale. The database is reset (wiped) at the end of the event so next year starts fresh.
- **Single test seam — the POS session facade**: the UI layer talks to one facade/interface exposing session operations (start session, set device name, load catalog, add item / set quantity, settle sale, void sale, correct sale, record cash adjustment, mark item sold-out, query running totals, query end-of-day figures, export CSV, wipe). All tests drive this facade as a black box with an in-memory persistence backing swapped in behind it. Real DB backing is used only by the production app, not by the test suite.
- **Settlement rules**: a sale may carry multiple tenders, but Octopus — when present — must equal the sale's total exactly (no partial Octopus, no Octopus combined with another method). Cash and vouchers may be combined in any split. Software must enforce these rules and reject an invalid settlement.
- **Change computation**: for the cash tender portion, the cashier enters the cash tendered; the app returns change = cash tendered − cash portion of the total. Handles whole-HKD amounts; still safe with cents.
- **Sequence numbers**: per-device, starting at 1 and incrementing per sale. A sale is numbered when it is settled; a correction reuses the original sale's number; a void keeps its original number too (and appears in the voids audit section). Both devices issue independent sequences, so the device name disambiguates.
- **Catalog**: loaded from a CSV with columns `Name, Price, Quantity`, comma-delimited with a header row. Items without a quantity (sell-by-demand) are allowed — the quantity cell is left blank. In-app additions and price fixes are allowed on top of the imported catalog. Items retain their identity after import; starting quantity is a one-time field for the stock check. The same CSV file is copied to both laptops by the organizer before the event (USB stick / shared drive); there is no on-the-day transfer.
- **Sold-out**: a per-device, manual flag the cashier sets when an item is physically gone. Dims the item in the list and prevents adding it to new sales. The app does not infer sold-out from quantity reaching zero across the shared stockpile, because the two laptops are unaware of each other's sales.
- **Corrections**: open an existing sale, modify items and/or settlement, save. The corrected sale replaces the prior state in totals. Logged in the export as the sale's final state, with the original creation time retained and an "updated" time recorded.
- **Voids**: set a sale's state to voided. The sale's items return to available (their quantity counts toward sold go away), the sale's amount no longer counts toward any total, but the voided sale is retained and emitted in a separate "voids" section of the export for audit.
- **Cash adjustments**: a distinct operation from sales — adds a positive or negative cash delta to the till, each carrying a time and a short reason. Adjustments modify expected cash but are not sales and never appear in sales totals.
- **Running totals**: the sale screen shows today's takings and sale count for this device, computed live from the persisted sales (excluding voids, including corrections' final state).
- **End-of-day view**: one screen per device showing expected cash = `float + cash sales (final-state, non-void) + cash added − cash removed`, total Octopus taken, total voucher value taken, per-item sold counts (final-state, non-void), and the voids list. All figures are per-device; the organizer manually combines both devices for the cross-device checks.
- **Sales cross-checks (manual, not automated)**: combined Octopus (A + B) vs the single shared Octopus machine's own report; combined per-item sold counts (A + B) vs physically counted leftover stock (`remaining = starting − sold A − sold B`). The app provides the per-device figures; the human does the combining.
- **Vouchers**: vouchers are received only at this stall (never sold here), bought with cash elsewhere on/before the day. **Resolved policy:** a voucher spends in full with no change given — if its value exceeds the sale total, the stall keeps the difference. The app records the sale value covered by vouchers (not the voucher's face value) and tracks total voucher value received per device; the organizer physically counts the paper vouchers. No per-denomination tracking.
- **Export shape**: two CSVs per device — `sales.csv` with columns `device, sale_seq, created_at, updated_at, status, total, cash, octopus, voucher`, and `items.csv` with columns `device, sale_seq, status, item, quantity, price`. Voids appear in the same files with `status=voided` so the organizer can filter them out of totals but still see them. UTF-8, comma-delimited, with a header row.
- **Conventions honoured**: per repo `docs/agents/domain.md`, the app's vocabulary uses the glossary in `CONTEXT.md` (Sale, Item, Float, Correction, Void, Cash adjustment, Octopus, Voucher, Split settlement, Sequence number, Device, Device name, Sales export, etc.). The two ADRs in `docs/adr/` (`0001-no-in-app-sync`, `0002-standalone-octopus`) stand and are not contradicted by this spec.

## Testing Decisions

- **What makes a good test**: tests assert the *external behavior* of the POS session facade, never its internal structure or the storage representation. A test passes an input (e.g. settle a sale with cash $30) and asserts an observable output (e.g. the next `end-of-day` query reports $30 cash, the running summary shows one sale, the export contains a `$30` row). A refactor that keeps behavior — swapping the pure-logic module, changing the DB schema, or replacing the in-memory backing — must not require changing any test.
- **One seam**: the `POS session` facade. The test suite drives only that interface. An `InMemoryPersistence` backing is injected behind the facade; the production SQLite backing is exercised by a separate, tiny round-trip sanity test (save a sale via the facade, reopen the DB file, assert the sale round-trips). The count of seams is one for the logic/most-of-the-app, plus the minimum needed to validate that the real DB implements the same persistence interface.
- **Modules under test**: the domain logic (totals, change, settlement-rule enforcement, sold-out, expected cash with adjustments, corrections' and voids' effect on totals, running totals, end-of-day figures, export rows), the facade's command/query interface, and the export CSV shape. Out of test: the UI layer and any Windows-specific glue.
- **Prior art**: none yet — this is a greenfield repo with no existing tests. The seam is chosen so future tests follow the same single pattern; no new seams are introduced for individual features.

## Out of Scope

- Syncing or merging the two laptops' databases in-app — explicitly rejected (ADR-0001). Cross-device combination is done by hand by the organizer via the CSV exports.
- Integrating the app with the Octopus machine's SDK/hardware — explicitly rejected (ADR-0002). The cashier records Octopus amounts manually; the machine keeps its own authoritative record.
- Refund flow — all sales final. The only correction path is voiding the original sale.
- Printing or rendering receipts — receipts are hand-written; the app never prints.
- Loyalty, discounts, bundles, haggling, or variable pricing — prices are fixed per item.
- Sales-tax/GST — prices are final; nothing is added at the register.
- Cashier identity or login — each laptop has one cashier at a time; the app tracks no per-user identity.
- Backup-to-USB or crash-recovery beyond write-per-sale — accepted risk for a one-day event; only the end-of-day CSV export is required.
- Multi-event history — the database is wiped at the end of the event; no year-over-year persistence of sales or catalog is required (the CSV is re-imported each year).
- Phone/tablet/web builds — Windows laptops only for this event.

## Further Notes

- **Resolved questions** (previously in `docs/open-questions.md`): (1) voucher change policy — spend in full, no change given; (2) voucher end-of-day handling — app tracks total voucher value received per device, organizer counts the paper vouchers; (3) CSV offline transfer — the organizer copies the same file to both laptops before the event; (4) CSV format — comma-delimited with a header row, items may have no quantity. None remain open.
- **ADRs already recording the surprising decisions**: `docs/adr/0001-no-in-app-sync.md` (why the two laptops don't sync), `docs/adr/0002-standalone-octopus.md` (why the app never drives the Octopus machine). Both stand.
- **Bilingual reality check**: though the team likely speaks English and the app is English-only (user story 40), all domain terms come from `CONTEXT.md` to keep the codebase, issue titles, and tests vocabulary-stable.
- **Build order hint** (not binding): catalog-load + setup → build-sale + settle → change + sequence number + write-per-sale → correction/void → cash adjustments + running totals → end-of-day view → CSV export → wipe-at-end. All slices are built; the voucher policy is resolved.
