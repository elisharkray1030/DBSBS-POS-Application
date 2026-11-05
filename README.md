# DBSBS POS Application

An offline point-of-sale application for a single stall at the DBS Garden Fete.
Runs on two Windows laptops with no network and no installer.

## Download & install (event laptops)

- Download the latest `DBSGardenFetePOS-v<tag>-windows.zip` from the
  [GitHub Releases page](https://github.com/elisharkray1030/DBSBS-POS-Application/releases/latest).
- Extract the zip to a writable folder, such as Documents. Do not run it from
  `Program Files` or a OneDrive-synced folder.
- Double-click `DBSGardenFetePOS.exe`. No console window appears. The app
  includes Python and its dependencies; no Python installation or internet
  connection is needed.
- The executable is unsigned. If Windows SmartScreen says **Windows protected
  your PC**, choose **More info** → **Run anyway**.
- On first run, the **setup screen** asks for the organizer's Stock sheet CSV
  (`ItemID, ItemName, Price, Inventory, Sales, Revenue`), starting float, and
  device name (e.g. "Till A"). After setup, the **sale screen** is the main
  working screen.
- The device database (`pos.db`), failure log (`pos.log`), and end-of-day
  exports are written next to the executable. Keep the extracted folder for
  the event so the data stays with that device.

## Run from source (developers)

- Install Python 3.11+ for Windows and copy or clone this folder.
- Double-click `start.pyw`. No console window appears. On first launch it
  installs the pinned `customtkinter` dependency if needed; do this once while
  connected to the internet. On later offline launches it starts directly.
- The source-run device database (`pos.db`) is created next to the launcher.
- On first run, the setup screen asks for the Stock sheet CSV, starting float,
  and device name.

From a Windows terminal, run `python start.pyw` (the dependency-bootstrapping
launcher) or `python main.pyw` (direct launch when dependencies are installed).

## Diagnostics

If something goes wrong on event day, the app records it locally — no console
or internet needed — in a `pos.log` file next to `pos.db` in the app folder.

- **First-run setup** verifies that the tested `customtkinter` release
  imports; an installed wrong or broken version is replaced, and a pip run is
  only treated as successful once the pinned version actually imports. Do
  this once per laptop while connected to the internet.
- **Install failures** show a message explaining whether it looks like a
  permissions or connectivity problem; the captured pip output is kept in
  `pos.log` (truncated to fit the log bound).
- **Startup failures** (e.g. the device database cannot be opened, or stored
  records are corrupted) show a window with the log location instead of
  failing silently.
- **Runtime errors** the register shows (export, settlement, corrections,
  voids, cash adjustments, sold-out, setup) are also written to `pos.log`. An
  unexpected failure inside a screen is logged and shown once in a fatal
  window, so a mid-event crash leaves a trace on the device.
- The log stays bounded (it never grows without limit). Every entry keeps its
  timestamp, the operation that failed, and its primary message; only an
  oversized detail is truncated. The log contains no secrets, so it can be
  handed to support safely.
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
an in-memory backing. The production app uses SQLite. The tkinter UI has no
automated tests. The app-data path helper has unit tests, and the release
workflow smoke-tests the packaged Windows executable by checking that it stays
open and creates `pos.db` beside itself; this does not replace a visual
rehearsal on the event laptops.

```bash
python -m pytest -q            # full suite
python -m mypy pos             # typecheck
python -m ruff check pos tests main.pyw start.pyw   # lint
```

See `docs/spec.md`, `CONTEXT.md`, and `docs/adr/` for the domain decisions.
