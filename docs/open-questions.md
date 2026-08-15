# Open Questions — resolved

All previously-open decisions were resolved with the stall's organizer on
2026-08-15. They are recorded here for history; the canonical spec
(`.scratch/dbsbs-pos/spec.md`) carries the final policy.

## Vouchers

- **Q: Denomination & change** — **Resolved:** a voucher spends in full with no
  change given. If a voucher's value exceeds the sale total, the stall keeps
  the difference. The app records the sale value covered by vouchers, not the
  voucher's face value. (The placeholder behavior shipped in the voucher
  tender is final.)
- **Q: End-of-day handling** — **Resolved:** the app tracks total voucher
  value received per device; the organizer physically counts the paper
  vouchers. No per-denomination tracking.

## CSV catalog

- **Q: Offline transfer to 2 devices** — **Resolved:** the organizer copies the
  same `Name, Price, Quantity` CSV to both laptops before the event (USB stick
  / shared drive). No on-the-day transfer.
- **Q: Format details** — **Resolved:** comma-delimited with a header row;
  items without a quantity (sell-by-demand) are allowed with a blank quantity.
