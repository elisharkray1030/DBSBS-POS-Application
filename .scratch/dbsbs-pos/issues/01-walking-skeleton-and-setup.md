# 01 — Walking skeleton + setup

**What to build:** The app launches on a Windows laptop to a setup screen with no network or install. The cashier loads the catalog from a `Name, Price, Quantity` CSV, enters the starting float, and names the device (e.g. "Till A"). All of it persists to a local database. This ticket also establishes the single POS session facade test seam with in-memory and real-database backings, so everything after it tests through that one interface.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] The app launches on Windows to a setup screen with no network and no installer
- [ ] Loading a CSV with columns `Name, Price, Quantity` creates the catalog
- [ ] The float and a device name can be entered and are persisted
- [ ] The POS session facade exists as the single seam, backed by both an in-memory and a real-database implementation
- [ ] A facade test passes against the in-memory backing, and a separate round-trip sanity test passes against the real database
