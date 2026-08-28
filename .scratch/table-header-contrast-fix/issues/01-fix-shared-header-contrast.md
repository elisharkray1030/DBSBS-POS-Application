# 01 — Fix shared Treeview header contrast across all tables

**What to build:** A centered fix so every data-table heading in the stall's app is legible in both light and dark appearances: sale screen Items table (Item ID, Item, Price, Remaining, Status) and Current sale table (Item, Qty, Total), Sales dialog Recorded sales table (Seq, Time, Status, Total) used for Correction and Void, and End of day screen tables for Items sold (Item, Sold), Voids (Seq, Time, Total), and Cash adjustments (Amount, Reason, Time). Covers the root-cause Windows theme failure and the locked high-contrast palette in one vertical slice.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Light appearance header uses pale background `#dbe4ee` with very dark foreground `#0f172a` (≈13.9:1) and dark appearance header uses `#333333` with white `#ffffff` (≈12.6:1); both are ≥4.5:1 and each header bar remains distinct from its body background (light body white vs. pale header, dark body `#242424` vs. `#333333`)
- [ ] Centralized styling configures heading and row styles from a single shared module/factory — no per-screen or per-dialog heading override — with theme selection to `clam` (Bundled Tk 8.6, respects heading colors) performed before any `Treeview`/`Treeview.Heading` configuration, falling back gracefully if unavailable, and hover/active heading maps to the same colors so headings do not wash out
- [ ] Headings legible via the four surfaces in both appearances: Items and Current sale on the sale screen, Recorded sales in the Sales dialog (including when opened for Correction), and all three End of day tables; dialogs show the correct appearance when opened after a change
- [ ] Appearance-watcher reapplies the shared styling when the OS/Ctk appearance toggles while the app is running (sale screen sold-out tag refreshed, theme re-selected); open dialogs are not required to repaint live — acceptable per Further Notes
- [ ] Selection highlight and sold-out dimming remain obvious in both appearances after the fix
- [ ] Tiny automated guard asserts the locked palette pairs and that the styling routine leaves `Treeview.Heading` background/foreground queryable as those values and the theme in a heading-respecting state (or graceful fallback)
- [ ] Existing `PosSession` facade suite (InMemory + SQLite round-trip) stays green; no change to Catalog, Sale, Cash, Octopus, Voucher, Split settlement, Sequence number, Correction, Void, Expected cash, Cash adjustment, Sales export, Device name, Float, Stock sheet, or glossary — manual Windows spot-check confirms headings readable light/dark across all surfaces
