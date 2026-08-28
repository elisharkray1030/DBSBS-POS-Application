# Stock sheet round-trip — the organizer's master file is both catalog input and completed report

The organizer keeps a master CSV of the stall's stock — one row per item — with
columns `ItemID, ItemName, Price, Inventory, Sales, Revenue`. We made that exact
file the app's **only** catalog input, and made the end-of-day export emit a new
file in the same six-column shape with only `Sales`/`Revenue` filled in, so the
master file returns to the organizer ready to be combined across devices.

The instinct is two separate formats: an app-specific catalog format
(`Name, Price, Quantity`) plus a separate export format. We rejected that.
Two formats mean the organizer maintains a translation layer; the register can
drift from the authoritative sheet; and merging the two devices' results means
reformatting before a pivot. With one round-trip format, the Item ID is the
item's identity from load to report, the catalog can be fully read-only (there
is nothing to add or fix in-app), and combining Till A and Till B is a simple
column join on `ItemID`.

## Considered options

- **App-specific catalog format + separate report format** — rejected: the
  organizer would maintain a translation between their sheet and the app, the
  register could diverge from the authoritative list, and end-of-day merging
  would need reformatting.
- **Keep in-app catalog editing (add item, fix price)** — rejected: cashiers
  editing items or prices silently diverges the register from the organizer's
  list. The Stock sheet is the single source of truth for what is sold and at
  what price, so the catalog is read-only once loaded.

## Consequences

- `ItemID` is the item's canonical identity; the loader rejects a missing or
  duplicate Item ID and a wrong header (including the old `Name, Price, Quantity`
  header). Pre-filled `Sales`/`Revenue` values in the loaded file are ignored.
- The catalog is read-only once loaded: the add-item and fix-price operations
  are removed from the session interface and every UI affordance for them.
- The end-of-day export writes a third file, `stocks-<device>.csv`, alongside
  `sales.csv` and `items.csv`: one row per catalog item in master-file order
  with the same six columns, `ItemID`/`ItemName`/`Price`/`Inventory` passed
  through unchanged, and only `Sales` (final-state, non-void units) and
  `Revenue` (actually-recorded settled value) filled. Items with no sales are
  written as `0`/`0`; a blank `Inventory` stays blank. The master file itself
  is never modified.
- The organizer still merges the two devices' reports by hand, per
  `0001-no-in-app-sync.md`.
