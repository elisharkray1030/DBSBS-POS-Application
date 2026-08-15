# Spec: Stock sheet round-trip

> Feature spec, published by `/to-spec` after the grilling session of 2026-08-15.
> **Status: ready-for-agent**
>
> Amends `.scratch/dbsbs-pos/spec.md`: this spec replaces the catalog input
> format (`Name, Price, Quantity` → the Stock sheet), makes the catalog
> read-only, and adds the Stock sheet report to the end-of-day export. All
> vocabulary follows `CONTEXT.md`; ADRs 0001 and 0002 stand.

## Problem Statement

The organizer keeps a master CSV of the stall's stock — one row per item —
with the columns `ItemID, ItemName, Price, Inventory, Sales, Revenue`. Today
the app assumes a different catalog format (`Name, Price, Quantity`), so the
file the organizer actually provides cannot be loaded. The app also lets
cashiers edit the catalog in-app (add items, fix prices), which silently
diverges the register from the organizer's authoritative list. And at the end
of the day there is no single report in the organizer's own format showing
what each item started with, sold, and earned — the stock check has to be
rebuilt by hand from other exports.

## Solution

The organizer's Stock sheet becomes the app's only catalog input and also the
shape of its end-of-day stock report. Each device loads the same master file
before the event: `ItemID` becomes the item's identity, `ItemName` its display
name, `Price` its fixed price, and `Inventory` its starting quantity. The
catalog is fully read-only once loaded — no in-app additions or price fixes.
At the end of the day each device exports its completed Stock sheet report (a
new file, same six columns, same row order) with `Sales` (units sold, final
state, excluding voids) and `Revenue` (actually-recorded settled value)
filled in from that device's own records; the source file is never modified.
The report is written alongside the existing `sales.csv` and `items.csv`
audit exports. The organizer merges the two devices' `Sales`/`Revenue`
columns by hand, as before.

## User Stories

1. As the stall's organizer, I want each device to load the catalog from the Stock sheet CSV with columns `ItemID, ItemName, Price, Inventory, Sales, Revenue`, so that the item list, fixed prices, and starting quantities all come from the one authoritative file.
2. As the stall's organizer, I want every item to carry its Item ID as its identity, so that a sale can always be traced back to exactly one row of the master file.
3. As the stall's organizer, I want the `ItemID` column to be required and unique per file, so that no two items collide and the round-trip report maps cleanly onto the master file.
4. As the stall's organizer, I want a clear error when the Stock sheet is missing or has a duplicate Item ID, so that a malformed file never loads silently.
5. As the stall's organizer, I want a clear error when the Stock sheet's header does not match `ItemID, ItemName, Price, Inventory, Sales, Revenue`, so that a wrongly-shaped file is rejected up front.
6. As the cashier, I want the item list to show each item's ID alongside its name, so that I can find items the organizer labels by code.
7. As the stall's organizer, I want the `Inventory` column to set each item's starting quantity, so that the end-of-day stock check is based on what the stall actually started with.
8. As the stall's organizer, I want items with a blank `Inventory` (sell-by-demand) to load without a starting quantity, so that the sheet can include items we sell without a fixed stock count.
9. As the stall's organizer, I want any `Sales` and `Revenue` values already present in the loaded file to be ignored, so that stale figures from a previous year never affect the day.
10. As the stall's organizer, I want the catalog to be fully read-only once loaded, so that the Stock sheet remains the single source of truth for what is sold and at what price.
11. As the stall's organizer, I want in-app catalog editing (adding items, fixing prices) removed, so that the register can never diverge from the Stock sheet.
12. As the stall's organizer, I want the old `Name, Price, Quantity` CSV format to no longer be accepted, so that there is exactly one catalog format.
13. As the stall's organizer, I want each device to export its completed Stock sheet report at the end of the day, so that the master file comes back with the device's results.
14. As the stall's organizer, I want the report to use the same six columns and header as the master file, so that I can combine devices' reports without reformatting.
15. As the stall's organizer, I want the report to preserve every row and the master file's row order, so that merging the two devices' reports is a simple column join.
16. As the stall's organizer, I want the app to fill only the `Sales` and `Revenue` columns, leaving `ItemID`, `ItemName`, `Price`, and `Inventory` untouched, so that the master file's data is never altered.
17. As the stall's organizer, I want the report written as a new file rather than overwriting the loaded master file, so that the original stays intact for my records.
18. As the stall's organizer, I want the report filename to carry the device name, so that Till A's and Till B's reports are distinguishable.
19. As the stall's organizer, I want `Sales` to be the number of units of that item sold on this device — final state, excluding voids — so that the stock check uses real sales.
20. As the stall's organizer, I want `Revenue` to be the actually-recorded settled value for that item on this device, so that the money figure matches what came in.
21. As the stall's organizer, I want a corrected sale to be reflected in the report in its final state, so that the report matches the day's totals.
22. As the stall's organizer, I want a voided sale to be excluded from both `Sales` and `Revenue`, so that cancelled sales do not inflate the stock check.
23. As the stall's organizer, I want items with no sales to be written as `Sales 0, Revenue 0`, so that every row of the report carries a value.
24. As the stall's organizer, I want an item with a blank `Inventory` to keep that cell blank in the report, so that the round-trip preserves the master file's intent.
25. As the stall's organizer, I want the Stock sheet report to be produced by the same export action as `sales.csv` and `items.csv`, so that nothing is forgotten at the end of the day.
26. As the stall's organizer, I want the existing `sales.csv` and `items.csv` exports to keep their current shape, so that the audit trail (tenders, sequence numbers, voids) is unchanged.
27. As the stall's organizer, I want the two devices' Stock sheet reports combined by hand, so that the app never merges devices (per ADR-0001).
28. As the stall's organizer, I want the wipe-at-end-of-event flow to be unchanged, so that next year starts from a clean slate.

## Implementation Decisions

- **Catalog input**: the only accepted catalog CSV has the header `ItemID, ItemName, Price, Inventory, Sales, Revenue`. The header is matched case-insensitively; a missing or wrong header is rejected. `ItemID` must be present and unique per file; `Price` must parse as money; `Inventory` is optional per row — blank means no starting quantity (sell-by-demand). `Sales` and `Revenue` are ignored at load time.
- **Item identity**: an item's identity is its Item ID (a string). The loader rejects a file with a missing or duplicate Item ID. In-app additions no longer exist, so every item in the catalog has an Item ID from load.
- **Read-only catalog**: the add-item and fix-price operations are removed from the session interface and the UI. The catalog is set exactly once, at setup, from the Stock sheet.
- **Item list**: the cashier-facing list shows both the Item ID and the item name. Selection and sale-building otherwise work as today.
- **Stock sheet report export**: the end-of-day export action writes a third file alongside `sales.csv` and `items.csv`, named after the device (e.g. `stocks-Till A.csv`). Its rows are the loaded catalog rows in master-file order, with the same six-column header; the `Sales` column is the item's final-state, non-void units sold on this device and the `Revenue` column is the sum of the actually-recorded settled line totals for that item (which reflects corrections and any in-app-disallowed price changes in their recorded form). Items with no sales are written as `0`/`0`; a blank `Inventory` is preserved as blank. The original master file is never written to.
- **Existing exports**: `sales.csv` and `items.csv` keep their current columns and semantics; the Stock sheet report is additive.
- **Cross-device**: each device's report reflects only that device's sales; the organizer combines the two reports' `Sales`/`Revenue` columns by hand (ADR-0001). The app never merges devices.

## Testing Decisions

- **What makes a good test**: tests assert only external behavior through the single POS session facade with an in-memory backing — e.g. load a six-column Stock sheet and observe the item list (IDs, prices, starting quantities); feed a duplicate/missing Item ID or wrong header and observe a load error; settle sales and observe the exported Stock sheet report's rows and `Sales`/`Revenue` values. A test never reaches into the loader's internals or the storage representation.
- **Modules under test**: the catalog loader (new format, validation, blank-inventory rule), the facade (load, list, and the three-file export), and the Stock sheet report's CSV shape and figures (voids excluded, corrections in final state, zero-fill, blank-inventory preservation, source untouched).
- **Seams**: unchanged — the single facade seam plus the existing SQLite round-trip sanity test. No new seams are introduced.
- **Prior art**: existing catalog-load tests (setup) and CSV-export shape tests (export) already drive these behaviours through the facade; the test fixtures' catalog sample is updated to the six-column format, and the export tests gain the Stock sheet report assertions.

## Out of Scope

- In-app catalog editing — deliberately removed.
- Merging the two devices' reports in-app — rejected by ADR-0001.
- Any change to the `sales.csv`/`items.csv` export shape.
- Any columns in the Stock sheet beyond the six (`ItemID, ItemName, Price, Inventory, Sales, Revenue`).
- Printing or rendering receipts, refunds, per-device syncing — all unchanged from the canonical spec.

## Further Notes

- Amends `.scratch/dbsbs-pos/spec.md`: user story 2 (catalog columns), the Catalog implementation decision, and the in-app catalog edits story are superseded; the export shape gains the Stock sheet report.
- `CONTEXT.md` was updated during the grilling session: new terms **Stock sheet** and **Item ID**; **Catalog** is now documented as read-only and loaded from the Stock sheet; **Starting quantity** comes from the `Inventory` column.
- An ADR-0003 (Stock sheet round-trip) was offered but not yet written; it should record why the organizer's master file is both catalog input and completed report rather than a separate export format.
