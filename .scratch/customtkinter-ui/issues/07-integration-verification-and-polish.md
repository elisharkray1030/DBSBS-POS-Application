# 07 — Integration verification and polish

**What to build:** A final end-to-end pass over the migrated app. Run the full manual regression of every cashier flow through the modern UI — setup, build and settle sales by each tender mode, correct, void, record a cash adjustment, mark sold-out, end-of-day, export, wipe — in both light and dark appearance, launched via the startup script from a copied folder, fully offline. Confirm the existing facade test suite still passes unchanged. Sweep up any residual polish that surfaces (window sizing, spacing, contrast).

**Blocked by:** 01, 02, 03, 04, 05, 06

**Status:** ready-for-agent

- [ ] Every flow works end-to-end: setup → build and settle sales by all tender modes → correct → void → cash adjustment → sold-out → end-of-day → export → wipe
- [ ] The app launches via the startup script from a copied folder, fully offline
- [ ] Light and dark appearance both render cleanly with no contrast, spacing, or layout issues
- [ ] All existing facade tests pass unchanged after the migration
- [ ] Residual polish (window size, spacing, contrast) found during the pass is resolved