# Spec: Deepen the Stock sheet round-trip module

> Feature spec for architecture umbrella U1 (#23), written from the grilling
> session of 2026-08-28. Amends the *implementation* posture of the shipped
> Stock sheet feature (`.scratch/stock-sheet/spec.md`, Status: done) without
> changing its behavior. Preserves ADR-0003; all vocabulary follows
> `CONTEXT.md`.

## Problem Statement

The Stock sheet round-trip is a real adapter seam mandated by ADR-0003, but its
behavior is spread across four modules. Loading validation lives in the catalog
loader, source-cell preservation lives on the domain `Item`, report-row
generation lives in the session facade, and the SQLite adapter persists the
leaked representation. A maintainer has to visit several modules to answer "how
does the round-trip preserve the master file's cells?" There is also no focused
coverage for malformed or ragged rows such as a missing `ItemName`, so a
badly-shaped file can load silently.

## Solution

The Stock sheet round-trip moves behind one new module. Loading, source-cell
preservation, and report-row generation all live there; the domain `Item` stops
carrying file-format cells; the session facade delegates row building to the
module and keeps writing the report file; and persistence round-trips the
preserved source cells through the module's contract. The behavior the
organizer depends on — the six-column round-trip, read-only catalog, per-device
export, lossless cell passthrough — is unchanged.

## User Stories

1. As the stall's organizer, I want the Stock sheet to keep loading with the six-column header `ItemID, ItemName, Price, Inventory, Sales, Revenue`, so that nothing about the file format changes.
2. As the stall's organizer, I want a clear error when a Stock sheet row is missing or has a blank `ItemName`, so that a ragged file never loads silently.
3. As the stall's organizer, I want the existing errors for a missing or duplicate Item ID and a wrong header to keep working, so that malformed files are still rejected up front.
4. As the stall's organizer, I want an empty Stock sheet file to be rejected, so that the app never runs with a catalog loaded from nothing.
5. As the stall's organizer, I want the item list to keep showing each item's ID, name, price, and starting quantity exactly as it does today, so that the deepening is invisible to the cashier.
6. As the stall's organizer, I want the Stock sheet report at the end of the day to keep the same six columns, header, and row order as the master file, so that merging the two devices' reports stays a column join.
7. As the stall's organizer, I want `ItemID`, `ItemName`, `Price`, and `Inventory` written back unchanged on the report, so that the master file's data round-trips losslessly.
8. As the stall's organizer, I want `Sales` and `Revenue` filled only for the device's own final-state, non-void sales, so that the stock check uses real numbers.
9. As the stall's organizer, I want an item with a blank `Inventory` to keep that cell blank in the report, so that sell-by-demand items stay unambiguous.
10. As the stall's organizer, I want items with no sales written as `Sales 0, Revenue 0`, so that every row of the report carries a value.
11. As the stall's organizer, I want the original master file never modified, so that my records stay intact.
12. As a maintainer, I want the round-trip rule (validation, source-cell preservation, report-row generation) to live behind one module, so that "how does the round-trip work?" has a single answer.
13. As a maintainer, I want the domain `Item` to carry only domain facts (ID, name, price, starting quantity, sold-out), so that file-format preservation stops leaking into the domain.
14. As a maintainer, I want the report-row generation to be callable directly for tests, so that the round-trip rule can be verified in isolation.
15. As a maintainer, I want the session facade to keep writing the report file, so that file I/O stays with the session and the exported files keep their current shape and names.
16. As a maintainer, I want the source cells to survive a device restart, so that the report still round-trips verbatim after the app is reopened.
17. As a maintainer, I want the SQLite adapter to persist the preserved source cells through the module's contract, so that storage is not coupled to the domain `Item` shape.
18. As a maintainer, I want the SQLite column that stores the preserved cells to be renamed to match the domain term, so that storage vocabulary agrees with the domain language.

## Implementation Decisions

- **Module home**: a new Stock sheet module owns validation, source-cell
  preservation, and report-row generation. The existing catalog loader is
  retired; its callers import from the new module.
- **Domain**: `Item.raw_cells` is removed. `Item` keeps only `item_id`, `name`,
  `price`, `starting_quantity`, and `sold_out`.
- **Source cells**: the four original cells (`ItemID, ItemName, Price,
  Inventory`) as delivered by the master file are a distinct concept owned by
  the module (glossary term "Source cells" added to `CONTEXT.md`). A
  source-cells map keyed by Item ID lives on the device settings, so it is
  persisted alongside the catalog and survives restart.
- **Module API**:
  - `load_catalog(path) -> LoadedCatalog` — validates the header, requires a
    non-empty file, requires each row's Item ID (present and unique) and
    ItemName (present and non-blank), parses Price and optional Inventory, and
    records the source cells for each item. `LoadedCatalog` carries the domain
    `Item`s and the source-cell map.
  - `build_report_rows(catalog_items, sold_by_item, source_cells) ->
    list[list[str]]` — builds the six-column report rows in catalog order,
    passing source cells through verbatim, synthesizing a fallback row from
    domain fields when source cells are absent, and appending the computed
    `Sales`/`Revenue`.
  - Source cells are owned by the module and carried on the device settings;
    the settings expose `source_cells_for(item_id)` for access.
- **Session facade**: the facade calls the module's loader, computes the
  per-item sold/revenue aggregation (final-state, non-void), asks the module
  for the report rows, and writes the report file itself. It no longer reads
  source cells off `Item`. The empty-file guard moves into the module.
- **Persistence**: the SQLite adapter stores the preserved source cells as a
  JSON column on the catalog record and hands the raw bytes back to the module
  to interpret. The adapter no longer reconstructs them through the domain
  `Item`. The column is renamed from the old leak-named `raw_cells` to
  `source_cells`, and the migration that upgrades older device databases is
  updated accordingly.
- **Header constant**: the six-column header constant moves to the module; the
  facade imports it from there.

## Testing Decisions

- **What makes a good test**: tests assert behavior, not internals. The module
  is tested through its public functions (load validation, report-row
  generation); the round-trip through the session is tested through the POS
  session interface with an in-memory backing, as today.
- **Modules under test**: the new Stock sheet module (isolated: ragged rows,
  missing/blank ItemName, empty file, source-cell passthrough, fallback
  synthesis), the session facade (load → list → export report shape), and the
  SQLite adapter (source-cell column round-trip, migration of older databases).
- **Seams**: two. The existing POS session facade remains the primary seam for
  round-trip behavior; the new Stock sheet module is the secondary seam for the
  validation and row-generation rules. The existing "single facade seam" testing
  posture is amended to admit the module seam.
- **Prior art**: the existing Stock sheet catalog and report tests drive
  load/export behavior through the facade and stay as round-trip coverage; the
  existing SQLite round-trip and migration tests cover the persistence side.
  The new module's unit tests follow the same black-box style against the
  module's public functions.

## Out of Scope

- Any change to the six-column Stock sheet format, header, or row order.
- Any change to the read-only catalog, Item ID identity, or per-device export rules (ADR-0003).
- Any change to the `sales.csv`/`items.csv` export shapes.
- The SQLite adapter's *deepening* beyond the source-cell column: schema-and-migration depth, consistency checks, and malformed-JSON handling are architecture umbrella U3's work.
- End-of-event reporting figures, tender totals, and void selection beyond what the Stock sheet report already does — that is architecture umbrella U2's work.
- Merging the two devices' reports in-app (ADR-0001) or any Octopus hardware integration (ADR-0002).

## Further Notes

- Amends the testing posture of `.scratch/stock-sheet/spec.md` (Status: done),
  which stated "No new seams are introduced": this umbrella admits one new
  module seam while keeping the session facade primary. The done feature spec is
  left untouched as the historical record of the shipped feature.
- `CONTEXT.md` was updated during the grilling session: new glossary term
  **Source cells**.
- This umbrella reinforces ADR-0003; no new ADR is warranted.
- The decisions here constrain U3 (`pos/sqlite.py` deepening): the module, not
  the domain `Item`, is the contract for preserved source cells.