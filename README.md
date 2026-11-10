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

## Clone and run from source (Windows)

The source-run workflow is for development and rehearsal. The application is
targeted and tested on 64-bit Windows; event laptops should use the packaged
release above. Before cloning on a fresh laptop, install or confirm:

- **64-bit Windows 10 or newer.** The source-run app is targeted and tested on
  Windows; macOS and Linux are not supported deployment targets.
- **Git for Windows**, including the `git` command-line tool
  ([download](https://git-scm.com/download/win)). No GitHub account is needed
  to clone this public repository.
- **64-bit Python 3.11 or newer for Windows** ([download](https://www.python.org/downloads/windows/)).
  Ensure the Python Launcher (`py`) and Tcl/Tk (`tkinter`) are installed; these
  are options in the Python installer. Python is needed for the source-run app.
- **Internet access for initial setup** to reach GitHub and install Python
  packages from PyPI. After dependencies are installed, the app runs offline.
- **A writable folder** for the clone, since the source app stores its local
  database and log in the repository folder.

PowerShell is included with Windows. No IDE, C/C++ compiler, database server,
or administrator account is required. Before proceeding, these commands should
work in a new PowerShell window:

```powershell
git --version
py -3 --version
```

In PowerShell, clone the repository and create an isolated environment:

```powershell
git clone https://github.com/elisharkray1030/DBSBS-POS-Application.git
cd DBSBS-POS-Application
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe start.pyw
```

The requirements install the pinned `customtkinter` runtime dependency and the
tools used for tests, type checking, and linting. To install only the app's
runtime dependency, use
`.\.venv\Scripts\python.exe -m pip install "customtkinter==6.0.0"` instead.
Alternatively, `start.pyw` installs that pinned dependency automatically when
it is missing, so the first launch still needs internet access. Once installed,
the source app can run offline. Use `start.pyw` as the normal launcher; it
surfaces startup errors and logs them. `main.pyw` is the direct launcher and
assumes the dependency is already installed.

The source-run device database (`pos.db`) and failure log (`pos.log`) are
created in the repository folder, which must be writable. Do not commit or
share those local files. On first run, the setup screen asks for the
organizer's Stock sheet CSV, starting float, and device name. No account,
credentials, server, or network configuration is needed by the app.

To run the automated checks after installing `requirements-dev.txt`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m mypy pos
.\.venv\Scripts\python.exe -m ruff check pos tests main.pyw start.pyw
```

## Diagnostics

If something goes wrong on event day, the app records it locally — no console
or internet needed — in a `pos.log` file next to `pos.db` in the app folder.

- The bootstrap details below apply only to the source-run workflow. The
  packaged executable already includes its dependency and does not run pip.
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
end-of-day report. The active Stock sheet filename is shown on the Sale and
End-of-day screens. Use **Change stock sheet…** on the Sale screen to select
another valid CSV; the catalog and prices for future sales then come from that
sheet. Use **Edit item…** to change an existing item's name, price, or starting
quantity in the local device database. Edits affect future sales only and do
not modify the selected source CSV; Item IDs cannot be added or removed. A
change or edit is blocked while the current sale has items; settle it or remove
the items first.

Changing sheets does not alter recorded sales: each sale keeps its original
item name and price, so the day's history can contain prices from more than one
sheet. The Stock sheet report uses the active sheet's row order and source
cells, while Sales and Revenue reflect the retained completed-sale history by
Item ID. Switching sheets invalidates a prior export; export again before
wiping recorded session data. The source filename (not its full path) is saved
with the device database. A configured device still resumes directly to Sale
on launch, using its saved catalog instead of rereading the CSV. Older
databases without a recorded filename show **Source not recorded** until a
sheet is selected. The master CSV itself is never modified, and the organizer
merges the two devices' reports by hand. See
`docs/adr/0003-stock-sheet-round-trip.md` and
`docs/adr/0007-active-stock-sheet-switching.md`.

## Screens

- **Setup** — load/select the Stock sheet CSV, enter the float, name the device.
- **Sale** — scrollable item list with Item IDs, live remaining counts and
  sold-out dimming; keyboard quick entry with `/` or keypad `/`; running total,
  settle with any combination of Cash / Voucher / Octopus, cash adjustments,
  corrections and voids; view/change the active Stock sheet.
- **End of day** — expected cash (float + cash sales + adjustments), Octopus
  total, voucher total, per-item sold counts, voids list; export three files
  (`sales.csv`, `items.csv`, and the device's Stock sheet report) and wipe the
  database for the end of the event (type `wipe` to confirm).

See [`docs/manual-acceptance.md`](docs/manual-acceptance.md) for the UI acceptance
checklist.

## Tenders

- Any non-empty combination of Cash, Octopus, and Voucher can settle a sale;
  each method has one positive portion and the portions must total the sale.
- Cash portion is recorded separately from Cash tendered, and change is based
  only on the Cash portion. Partial Octopus is recorded for reconciliation with
  the shared machine.
- A voucher spends in full with no change given; the app records the sale
  value covered by vouchers and shows the total voucher value per device.

## Development

The core logic is tested through a single seam, the POS session facade, with
an in-memory backing. The production app uses SQLite. The tkinter UI has no
automated tests. The app-data path helper has unit tests, and the release
workflow smoke-tests the packaged Windows executable by checking that it stays
open and creates `pos.db` beside itself; this does not replace a visual
rehearsal on the event laptops.

See `docs/spec.md`, `CONTEXT.md`, and `docs/adr/` for the domain decisions.
