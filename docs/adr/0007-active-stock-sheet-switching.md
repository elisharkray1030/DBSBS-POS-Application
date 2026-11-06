# The active Stock sheet can change without rewriting recorded sales

The active Stock sheet supplies the current catalog, source cells, and prices
for future sales and the Stock sheet report. An operator may change it from the
Sale screen during the event, rather than being locked to the first CSV loaded.
The selected filename is persisted as a basename; the catalog already stored
in the device database remains authoritative on relaunch and is not reread from
the CSV path.

Changing sheets does not rewrite, re-price, or remove recorded sales. A sale
line is a historical snapshot of its Item ID, item name, quantity, and unit
price at settlement, and totals continue to derive from those recorded lines.
Consequently, a day's history may contain prices from multiple sheets. The
Stock sheet report follows the active sheet's row order and source cells, while
Sales and Revenue are aggregated from retained completed sales by Item ID.
Items sold earlier that are absent from the active catalog remain visible in
the end-of-day sold-item summary through the existing Item ID fallback.

A sheet change is rejected while the current sale contains items: the operator
must settle it or remove its items first. The CSV is parsed and validated
before a single candidate settings state is persisted. A failed read or write
leaves the active catalog, source cells, filename, export state, and recorded
sales unchanged. A successful change clears the last-export timestamp so the
existing wipe safeguard requires an export based on the new active sheet
before recorded sales can be wiped.

The operator may edit the active catalog's item name, price, and starting
quantity from the Sale screen, but may not add or remove Item IDs. Edits are
stored in the device database, never written back to the selected source CSV,
and are blocked while the current sale has items. Future sale lines use edited
values; historical sale snapshots do not change. Starting-quantity edits set a
new baseline, with remaining quantity computed as that baseline minus all
completed non-void units sold for the Item ID in the shared event history,
clamped at zero for display. If the recalculated remaining quantity is
positive, a starting-quantity edit clears that item's manual sold-out flag.
Catalog edits invalidate the previous export just like a sheet switch. The explicit
end-of-day export uses the edited active catalog values for its Stock sheet
rows and actual recorded history for Sales and Revenue; the selected source
file remains untouched.

## Considered options

- **Keep the first-loaded catalog for the whole event** — rejected: organizers
  may need to choose a different valid price variant after setup, and the active
  source must be apparent to the cashier and in the final report.
- **Rewrite or re-price history to match the newly selected catalog** —
  rejected: recorded sale lines are durable evidence of the actual items and
  amounts settled; changing them would corrupt revenue and payment records.
- **Persist and reread an absolute CSV path at startup** — rejected: a saved
  catalog is already part of the device database and must resume offline even
  if the source file was moved or is unavailable. Persist only its basename for
  operator visibility.

## Consequences

- The Sale screen identifies the active filename and offers a guarded change
  action; End-of-day shows the same filename. Older databases without the
  filename show **Source not recorded** until a sheet is selected.
- A changed sheet affects only future sales and the active Stock sheet rows;
  historical sale snapshots and sale-derived totals remain unchanged.
- Changing the catalog/source invalidates a previous export. The operator must
  export again before wiping the device.
- Selecting a different valid source is allowed, and existing catalog rows can
  be edited in-app; adding or removing Item IDs is not supported.
