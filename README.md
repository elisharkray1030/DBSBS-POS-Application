# DBSBS POS Application

An offline point-of-sale application for a single stall at the DBS Garden Fete.
Runs on two Windows laptops with no network and no installer.

## Run it

- Install Python 3.11+ for Windows.
- Copy this whole folder to each laptop.
- Double-click `start.pyw`. No console window appears. On first launch it
  installs the one external dependency (`customtkinter`, the tested version)
  if needed — do this once per laptop while connected to the internet — then
  launches the app. On event day (no internet) the dependency is already
  installed and the script goes straight to launching. The local database
  (`pos.db`) is created next to the launcher on first run.
- On first run you reach the **setup screen**: load the organizer's Stock sheet
  CSV (`ItemID, ItemName, Price, Inventory, Sales, Revenue`), enter the
  starting float, and name the device (e.g. "Till A"). After that the
  **sale screen** is the main working screen.

Alternatively run `python start.pyw` or `python main.pyw` from a terminal.

## Diagnostics

If something goes wrong on event day, the app records it locally — no console
or internet needed — in a `pos.log` file next to `pos.db` in the app folder.

- **First-run setup** installs the tested `customtkinter` version, so the UI
  is exactly what the app was verified against. Do this once per laptop while
  connected to the internet.
- **Install failures** show a message explaining whether it looks like a
  permissions or connectivity problem; the full pip output is kept in
  `pos.log`.
- **Startup failures** (e.g. the device database cannot be opened, or stored
  records are corrupted) show a window with the log location instead of
  failing silently.
- **Runtime errors** the register shows (export, settlement, corrections,
  voids, cash adjustments, sold-out, setup) are also written to `pos.log`.
- The log stays bounded (it never grows without limit) and contains no
  secrets, so it can be handed to support safely.
- A normal event-day startup is silent: the app just launches.

## Stock sheet round-trip

The organizer's master CSV is both the app's catalog input and the shape of its
end-of-day report. The catalog is loaded once from the Stock sheet and is
**read-only** — there is no in-app way to add an item or change a price.
At the end of the day each device exports its completed Stock sheet report
(`stocks-<device>.csv`) with the same six columns and one row per catalog item
in the master file's order; only `Sales` (units sold, final state, excluding
voids) and `Revenue` (actually-recorded settled value) are filled. The master
file itself is never modified, and the organizer merges the two devices'
reports by hand. See `docs/adr/0003-stock-sheet-round-trip.md`.

## Screens

- **Setup** — load the Stock sheet CSV, enter the float, name the device.
- **Sale** — scrollable item list with Item IDs, live remaining counts and
  sold-out dimming, running total, settle by cash / voucher / Octopus /
  cash+voucher, cash adjustments, corrections and voids.
- **End of day** — expected cash (float + cash sales + adjustments), Octopus
  total, voucher total, per-item sold counts, voids list; export three files
  (`sales.csv`, `items.csv`, and the device's Stock sheet report) and wipe the
  database for the end of the event (type `wipe` to confirm).

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
python -m ruff check pos tests main.pyw start.pyw   # lint
```

See `docs/spec.md`, `CONTEXT.md`, and `docs/adr/` for the domain decisions.
