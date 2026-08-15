# 04 — Record the Stock sheet round-trip decision and reconcile docs

**What to build:** The round-trip design is recorded and the docs stop contradicting the new behaviour: write ADR-0003 capturing why the organizer's master file is both the catalog input and the completed report rather than a separate export format, amend the canonical spec's catalog-format, read-only-catalog, and export sections, and update the README's catalog and export descriptions so it no longer describes the old `Name, Price, Quantity` format.

**Blocked by:** 02 — Read-only catalog; 03 — Export the completed Stock sheet report.

**Status:** ready-for-agent

- [ ] ADR-0003 records the Stock sheet round-trip decision and the trade-off it resolves
- [ ] The canonical spec reflects the Stock sheet format, the read-only catalog (no in-app edits), and the three-file export
- [ ] The README no longer describes the `Name, Price, Quantity` catalog format and mentions the Stock sheet report
