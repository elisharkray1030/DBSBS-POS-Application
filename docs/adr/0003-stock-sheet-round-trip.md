# Stock sheet round-trip — the organizer's master file is both catalog input and completed report

The organizer keeps a master CSV of the stall's stock — one row per item — with
columns `ItemID, ItemName, Price, Inventory, Sales, Revenue`. That file is the
app's catalog input. The end-of-day export emits a new file in the same
six-column shape: it preserves each Item ID, uses the active device catalog's
name, price, and `Inventory` value (including local edits), and fills `Sales`/`Revenue`
from recorded history. The source master file is never modified.

The instinct is two separate formats: an app-specific catalog format
(`Name, Price, Quantity`) plus a separate export format. We rejected that.
Two formats mean the organizer maintains a translation layer; the register can
drift from the authoritative sheet; and merging the two devices' results means
reformatting before a pivot. With one round-trip format, the Item ID remains the
item's identity from load to report, and combining Till A and Till B is a simple
column join on `ItemID`. ADR-0007 permits device-local edits to existing item
names, prices, and starting quantities during the event; Item IDs cannot be added or
removed, and those edits never change the organizer's source file.

## Considered options

- **App-specific catalog format + separate report format** — rejected: the
  organizer would maintain a translation between their sheet and the app, the
  register could diverge from the authoritative list, and end-of-day merging
  would need reformatting.
- **Edit the organizer's master CSV in place** — rejected: the source file must
  remain untouched. ADR-0007 permits edits to the device's local catalog copy
  without writing back to the selected CSV.

## Consequences

- `ItemID` is the item's canonical identity; the loader rejects a missing or
  duplicate Item ID and a wrong header (including the old `Name, Price, Quantity`
  header). Pre-filled `Sales`/`Revenue` values in the loaded file are ignored.
- The app does not add or remove Item IDs. The operator may select another
  valid Stock sheet and edit existing item names, prices, and starting
  quantities on the device during the event; see
  `0007-active-stock-sheet-switching.md` for how
  those edits preserve sale history without changing the source CSV.
- The end-of-day export writes a third file, `stocks-<device>.csv`, alongside
  `sales.csv` and `items.csv`: one row per catalog item in master-file order
  with the same six columns. When source cells are available, `ItemID` is
  passed through unchanged; otherwise the canonical Item ID is used.
  `ItemName`/`Price`/`Inventory` reflect the active device catalog and otherwise
  retain their source cells. `Sales` (final-state, non-void units) and `Revenue`
  (actually-recorded settled value) are computed from recorded sales. Items
  with no sales are written as `0`/`0`; a blank `Inventory` stays blank unless
  edited in the device catalog. The master file itself is never modified.
- The organizer still merges the two devices' reports by hand, per
  `0001-no-in-app-sync.md`.
