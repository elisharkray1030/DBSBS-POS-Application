# 02 — Read-only catalog: item list shows Item ID and name, no in-app editing

**What to build:** The cashier-facing item list shows each item's Item ID alongside its name, so cashiers can find items the organizer labels by code, while the list keeps its current remaining counts and sold-out dimming. The add-item and fix-price operations are removed from the session interface and every UI affordance for them is gone; the Stock sheet is the only way the catalog is set, and it cannot be changed after load.

**Blocked by:** 01 — Load the organizer's Stock sheet as the catalog.

**Status:** ready-for-agent

- [ ] Each row of the sale-screen item list shows the item's Item ID and its name
- [ ] Remaining counts and sold-out dimming behave exactly as today
- [ ] The add-item and fix-price operations no longer exist on the session facade
- [ ] No UI affordance remains for adding an item or fixing a price
- [ ] The catalog cannot be changed after it is loaded
