# Durable sale record — a sale is its line items and tenders; figures are derived

A sale's durable record in the device database is its line items and tenders,
stored as JSON. Total, cash, octopus, and voucher figures are derived from
those on read and never stored. We rejected keeping the summary columns beside
the JSON: they were write-only redundancy with no reader, and they created a
consistency obligation (whoever changed how a total is computed would have to
remember to update the columns). A single representation keeps reconstruction
single-sourced and makes a corrupt record fail loudly instead of being silently
reconciled against a duplicate.

## Considered options

- **Store summary columns and verify them on read** — rejected: the only value
  of the columns was integrity checking, which a corruption error already
  provides without a second representation to keep in agreement.

## Consequences

- The `sales` table stores `line_items` and `tenders` JSON only; databases
  created by older code drop the four summary columns via the migration ladder.
- A sale is reconstructed from its JSON; a record that cannot be parsed is a
  `CorruptRecordError`, never a guessed figure.
