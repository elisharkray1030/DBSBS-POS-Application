# DBSBS POS Application

An offline point-of-sale application for a single stall at the DBS Garden Fete.
Runs on two Windows laptops with no network and no installer.

## Run it

- Install Python 3.11+ for Windows.
- Copy this whole folder to each laptop.
- Double-click `main.pyw`. No console window appears. The local database
  (`pos.db`) is created next to the launcher on first run.
- On first run you reach the **setup screen**: load the catalog CSV
  (`Name, Price, Quantity`), enter the starting float, and name the device
  (e.g. "Till A"). After that the **sale screen** is the main working screen.

Alternatively run `python main.pyw` from a terminal.

## Screens

- **Setup** — load catalog CSV, enter float, name the device.
- **Sale** — scrollable item list with live remaining counts and sold-out
  dimming, running total, settle by cash / voucher / Octopus / cash+voucher,
  cash adjustments, in-app catalog edits, corrections and voids.
- **End of day** — expected cash (float + cash sales + adjustments), Octopus
  total, voucher total, per-item sold counts, voids list; export two CSVs and
  wipe the database for the end of the event (type `wipe` to confirm).

## Tenders

- Cash and vouchers may be split across one sale in any combination.
- Octopus always settles the full sale on its own; partial or combined Octopus
  is rejected.
- A voucher spends in full with no change given; the app records the sale
  value covered by vouchers and shows the total voucher value per device.

## Development

The core logic is tested through a single seam, the POS session facade, with
an in-memory backing. The production app uses SQLite. The tkinter UI and
Windows glue are intentionally untested.

```bash
python -m pytest -q            # full suite
python -m mypy pos             # typecheck
python -m ruff check pos tests main.pyw   # lint
```

See `docs/spec.md`, `CONTEXT.md`, and `docs/adr/` for the domain decisions.
