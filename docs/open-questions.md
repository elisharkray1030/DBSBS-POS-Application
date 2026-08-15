# Open Questions

Decisions not yet confirmed. Items here block downstream design; resolve them with the stall's organizer before implementation.

## Vouchers

- **Q: Denomination & change** — What value(s) do vouchers come in? If a sale totals less than a voucher's value, does the stall give change, allow the voucher to cover multiple sales, or spend it in full with no change?
- **Q: End-of-day handling** — What happens to collected vouchers at the end of the event? Are they counted/handed back to the organizer? Does the app need to track how many vouchers were collected?

## CSV catalog

- **Q: Offline transfer to 2 devices** — There are two devices and no wifi. How does the CSV (and any per-device config) get onto both? (Copy the same file to both / load on one and export to the other / shared drive.)
- **Q: Format details** — Confirmed as `Name, Price, Quantity`. Confirm the delimiter (comma vs tab) and whether quantities for all items are present, or some items have no quantity (sell-by-demand).
