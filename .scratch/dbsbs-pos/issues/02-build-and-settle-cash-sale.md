# 02 — Build & settle a cash sale

**What to build:** The cashier builds a sale from a scrollable item list showing live remaining counts, sees a running total, then settles it in cash. The app computes the change due, assigns a sequence number and timestamp, and writes the completed sale to disk immediately so a crash never loses it. The customer's receipt stays hand-written; the app only records the sale.

**Blocked by:** 01 — Walking skeleton + setup

**Status:** ready-for-agent

- [ ] A scrollable list shows all items with their remaining counts
- [ ] The cashier can add an item to the current sale with a quantity, and the running total updates
- [ ] Settling a cash sale accepts the cash tendered and shows the change due
- [ ] Each completed sale gets a sequence number and timestamp
- [ ] A completed sale is written to disk the moment it's made and survives a simulated crash
