# 09 — Wipe at end of event

**What to build:** A deliberate, confirmed action wipes the local database when the event ends, so next year's event starts from a blank slate — new setup screen, empty catalog, no leftover sales. The wipe happens only after the end-of-day export has been taken.

**Blocked by:** 08 — CSV export

**Status:** ready-for-agent

- [ ] A confirmed action wipes the local database (catalog, sales, adjustments, settings)
- [ ] After wiping, the app returns to the setup screen as if new
- [ ] The wipe requires confirmation and cannot be triggered accidentally
