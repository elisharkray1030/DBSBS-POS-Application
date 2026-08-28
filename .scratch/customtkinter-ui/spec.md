# Spec: CustomTkinter UI migration

> Feature spec, published by `/to-spec`.
> **Status: done**
>
> Does not amend the canonical spec (`.scratch/dbsbs-pos/spec.md`) or the
> Stock sheet spec (`.scratch/stock-sheet/spec.md`) — all functional behavior
> is unchanged. This spec covers only the visual/UI layer and the deployment
> glue for the new dependency. All vocabulary follows `CONTEXT.md`; ADRs 0001,
> 0002, and 0003 stand and are not contradicted.

## Problem Statement

The DBS Garden Fete POS works, but its tkinter/ttk user interface looks dated.
The cashier-facing screens (setup, sale, end-of-day) and all dialogs use stock
ttk widgets with no theming, no rounded corners, no hover states, and poor
high-DPI scaling — stock tkinter renders blurry or tiny on modern Windows
laptops. For a POS used at a public-facing school charity event with
non-technical cashiers, the visual quality should feel modern and professional,
and buttons should be large enough to tap confidently during busy periods. The
underlying application logic is correct and well-tested; only the appearance
and widget quality fall short.

## Solution

Replace the tkinter/ttk widget layer with **CustomTkinter** (ctk), a
modern-looking wrapper built on top of tkinter that provides rounded buttons
with hover states, clean entry fields with focus borders, themed frames, and
automatic high-DPI scaling. The `PosSession` facade, domain logic, catalog
loader, and persistence layers remain completely unchanged — only the UI layer
(`pos/ui/`) is migrated. Data tables (`ttk.Treeview`, used for six lists across
the app) are retained as Treeview but restyled via `ttk.Style` to match the
CustomTkinter color scheme, because CustomTkinter has no native table widget
and Treeview remains the proven, lowest-risk option. A new **startup script**
handles the `customtkinter` dependency: it checks whether the package is
importable, installs it via pip if missing, then launches the application —
preserving the double-click deployment model. The app defaults to the system
appearance mode (light or dark, following the Windows setting).

## User Stories

1. As a cashier, I want the app to look modern and clean, so that it feels professional when serving customers at the stall.
2. As a cashier, I want buttons with rounded corners and clear hover states, so that interactive elements are obvious and feel responsive.
3. As a cashier, I want entry fields with rounded borders and clear focus states, so that I can see which field I'm typing in.
4. As a cashier, I want labels and text to use clean, readable typography, so that I can scan information quickly.
5. As a cashier, I want frames and sections to have subtle borders or backgrounds, so that the layout is visually organized rather than flat.
6. As a cashier, I want the app to follow my system's light/dark appearance setting, so that it matches my laptop's look and doesn't clash.
7. As a cashier, I want the app to have a consistent color theme across all screens and dialogs, so that it feels like one cohesive application.
8. As a cashier, I want the app to scale properly on high-DPI displays, so that text and buttons are sharp and appropriately sized on modern laptops.
9. As a cashier, I want the app's buttons to be sized for touch and mouse use, so that I can quickly tap them during busy periods.
10. As a cashier, I want the data tables (item list, current sale, sold counts, voids, cash adjustments, sales list) to be styled to match the rest of the app, so that they don't look out of place against the modern widgets.
11. As a cashier, I want the data table headers to use the app's color theme, so that they look consistent with the surrounding widgets.
12. As a cashier, I want the data table rows to have adequate row height and spacing, so that I can scan and select rows quickly.
13. As a cashier, I want the data table selection highlight to use the app's accent color, so that the selected row is obvious at a glance.
14. As a cashier, I want sold-out items in the item list to remain visually distinct with dimmed text, so that the Treeview restyling doesn't lose this cue.
15. As a cashier, I want the setup screen to have clear field labels and adequate spacing, so that I don't make input errors when starting the day.
16. As a cashier, I want the sale screen's item list to still show item IDs, names, prices, and remaining counts in a scrollable table, so that I can find any of the 30-40 items.
17. As a cashier, I want the current sale panel to still show line items, quantities, and the running total, so that I can see what the customer owes.
18. As a cashier, I want the current sale total to be displayed in a larger, prominent font, so that I can quickly tell the customer the amount.
19. As a cashier, I want the settle button on the sale screen to be visually prominent, so that I can find it quickly during busy periods.
20. As a cashier, I want the settle dialog to still let me choose cash, voucher, Octopus, or cash+voucher, so that I can take any payment combination.
21. As a cashier, I want the sales dialog to still list recorded sales for correction or voiding, so that I can fix mistakes.
22. As a cashier, I want the correction dialog to still let me edit line items and re-settle, so that I can correct a sale in place.
23. As a cashier, I want the cash adjustment dialog to still record cash added or removed with a reason, so that expected cash stays accurate.
24. As a cashier, I want the end-of-day screen to still show expected cash, Octopus total, voucher total, per-item sold counts, voids, and cash adjustments, so that I can reconcile.
25. As a cashier, I want the end-of-day screen to have clear section separation between the cash figures, sold counts, voids, and adjustments, so that reconciliation is easy to read.
26. As a cashier, I want the end-of-day action buttons (export, wipe) to be clearly placed and distinct from the back-to-sales navigation, so that I don't confuse them.
27. As a cashier, I want the export dialog to still let me choose a folder and write the three CSV files, so that I can hand the organizer the device's data.
28. As a cashier, I want the wipe dialog to still require typing 'wipe' to confirm, so that the database is never erased accidentally.
29. As a cashier, I want the running summary to still show today's takings and sale count on the sale screen, so that I can glance at the day's progress.
30. As the organizer, I want a startup script that checks whether the app's dependencies are installed, so that I don't have to manually run pip commands.
31. As the organizer, I want the startup script to install missing dependencies automatically, so that the first launch on a new laptop sets itself up.
32. As the organizer, I want the startup script to launch the app after ensuring dependencies are present, so that double-clicking one file gets me to the register.
33. As the organizer, I want the app to still run fully offline on event day, so that it works at the fete with no network (dependencies are installed before the event, when internet is available).
34. As the organizer, I want the app to still be double-clickable on Windows with no installer, so that anyone at the stall can launch it.
35. As the organizer, I want the app to still run from a copied folder with no setup beyond the startup script, so that deployment stays simple.
36. As the organizer, I want the app to use only the Python standard library plus customtkinter, so that the dependency footprint stays minimal and predictable.
37. As the organizer, I want the app's entire interface to remain in English, so that the team can read everything.
38. As a cashier, I want all existing functionality to work exactly as before after the visual upgrade, so that nothing breaks during the migration.
39. As a developer, I want the PosSession facade to remain the single test seam, so that the existing test suite validates that the migration didn't break anything.
40. As a developer, I want the UI layer to remain untested by design, so that the test suite stays focused on behavioral correctness through the facade.
41. As a developer, I want the migration to be a like-for-like widget replacement, so that the facade contract and domain logic are unchanged.
42. As a developer, I want the startup script to be the only new non-UI file, so that the change is contained to the UI layer plus deployment glue.
43. As a developer, I want tkinter's filedialog and messagebox to remain available, so that file picking and alert dialogs work without replacement (CustomTkinter is built on tkinter).

## Implementation Decisions

- **UI framework**: Replace `tkinter`/`ttk` imports with `customtkinter` (ctk) throughout `pos/ui/`. CustomTkinter is built on tkinter, so tkinter's `filedialog` and `messagebox` remain available and are used as-is for file picking and alert dialogs — no replacement needed.
- **Application shell**: `PosApp` changes from `tk.Tk` to `ctk.CTk`. At startup, `ctk.set_appearance_mode("system")` is called so the app follows the Windows light/dark setting. A default color theme (the built-in blue or green) is set via `ctk.set_default_color_theme`. The screen-replacement pattern (destroy current frame, pack new one) is unchanged.
- **Screens**: `SetupScreen`, `SaleScreen`, `EndOfDayScreen` change from `ttk.Frame` to `ctk.CTkFrame`. All `ttk.Label` → `ctk.CTkLabel`, `ttk.Button` → `ctk.CTkButton`, `ttk.Entry` → `ctk.CTkEntry`, `ttk.Frame` → `ctk.CTkFrame`, `ttk.PanedWindow` → `ctk.CTkFrame`-based layout (or retained as ttk.PanedWindow if it restyles acceptably). The layout logic (pack/grid), event handlers, and `refresh()` methods are unchanged.
- **Dialogs**: All dialog classes (`SettleDialog`, `AdjustmentDialog`, `SalesDialog`, `CorrectionDialog`, `ExportDialog`, `WipeDialog`) change from `tk.Toplevel` to `ctk.CTkToplevel`. `TenderSection` changes from `ttk.LabelFrame` to `ctk.CTkFrame`. `ttk.Radiobutton` → `ctk.CTkRadioButton`, `ttk.Combobox` → `ctk.CTkComboBox`. The `run_dialog` / `grab_set` / `wait_window` modal pattern is unchanged.
- **Data tables (ttk.Treeview)**: Retained as `ttk.Treeview` for all six tables (item list, current sale, sold counts, voids, cash adjustments, sales list). Styled via `ttk.Style` to match the CTk color theme: custom header background and foreground colors, row height, selection highlight color, and font. The `sold_out` tag configuration is preserved with a dimmed foreground that adapts to the active appearance mode (light vs. dark). Treeview is used inside CTk frames; the parent frame provides the rounded border and background.
- **Appearance mode**: Defaults to `"system"` (follows the Windows light/dark setting). The Treeview styling reads the active appearance mode and applies matching colors, so the tables stay consistent if the OS theme changes.
- **High-DPI scaling**: CustomTkinter handles DPI scaling automatically — a key advantage over stock tkinter. No manual `tk.call('tk', 'scaling', …)` or DPI-awareness code is needed.
- **Window size**: The current `1000x640` is retained as the default but may be adjusted upward if the new widget sizing requires more room. The layout proportions (item list weight 3, sale panel weight 2) are preserved.
- **Dependency management — startup script**: A new startup script is the double-click entry point (replacing direct double-click on `main.pyw`). It:
  1. Checks whether `customtkinter` is importable (a lightweight `import` attempt).
  2. If the import fails, runs `pip install customtkinter` via `subprocess`. This requires internet and is expected to happen before the event, when the organizer first copies the folder to each laptop.
  3. Once the dependency is confirmed present, launches the application (calls `main` from `main.pyw` or launches it as a subprocess with `pythonw` to avoid a console window).
  On event day (no internet), the dependency is already installed and the script proceeds straight to launching the app. If the dependency is missing and pip cannot reach the network, the script shows a clear error message telling the organizer to run the script once with internet first.
- **Dependency footprint**: The only external dependency is `customtkinter` (which itself depends on `tkinter`, already in the Python standard library on Windows). No other packages are added. The previous "zero external dependencies" property is relaxed to "one external dependency, managed by the startup script."
- **Facade / domain / persistence — unchanged**: The `PosSession` interface, domain types (`Item`, `Sale`, `LineItem`, `Tender`, `EndOfDay`, `RunningSummary`, etc.), `SqlitePersistence`, `InMemoryPersistence`, and the catalog loader are completely untouched. The UI layer calls the same facade methods with the same arguments. No schema changes, no API contract changes.
- **main.pyw**: Largely unchanged — still creates `PosSession` with `SqlitePersistence` and launches `PosApp`. The `ctk` appearance/theme setup is added at the top of the `PosApp` constructor (or in `main()` before constructing `PosApp`).
- **StringVar compatibility**: CustomTkinter widgets accept `tk.StringVar` for `textvariable` the same way ttk widgets do, so the existing `StringVar`-based state tracking (summary label, total label, CSV path, float, device name, quantity entries) works without changes.

## Testing Decisions

- **What makes a good test**: unchanged from the canonical spec — tests assert only external behavior through the `PosSession` facade, never UI internals or widget structure. A UI widget swap must not require any test changes. If a test breaks, it means the migration touched the facade or domain layer, which is out of scope.
- **No new seams**: the existing `PosSession` facade seam plus the SQLite round-trip sanity test remain the only seams. The UI layer stays untested by design, consistent with the canonical spec's testing decisions. No UI tests, screenshot tests, or widget-level tests are added.
- **Modules under test**: unchanged — the facade, domain logic (totals, change, settlement rules, sold-out, expected cash, corrections, voids, running totals, end-of-day figures), and export CSV shape. The UI layer and the startup script are out of test.
- **Validation approach for the migration**:
  - All existing facade tests (13 test files, ~1,100 lines) must pass unchanged after the migration. This is the regression net — it proves the backend is untouched.
  - Manual verification: the app launches via the startup script, all three screens (setup, sale, end-of-day) render with the new CustomTkinter widgets, all operations work end-to-end (load catalog, build sale, settle by each tender method, correct, void, record adjustment, mark sold-out, export, wipe), and the Treeview tables are restyled to match.
  - Manual verification of the startup script: on a machine without `customtkinter`, the script installs it and launches; on a machine with it already installed, the script launches directly.
- **Prior art**: the existing test suite is the prior art and remains the regression net. No new test patterns are introduced.

## Out of Scope

- No changes to the `PosSession` facade, domain types, persistence layer, catalog loader, or export logic.
- No new features — no new payment methods, no receipt printing, no sync, no multi-event history, no loyalty/discounts, no cashier login.
- No mobile, web, or tablet builds — Windows laptops only.
- No replacement of `ttk.Treeview` with a different table widget (Treeview is retained and restyled).
- No bundling with PyInstaller, cx_Freeze, or similar — the startup script handles the dependency at runtime.
- No automated UI, screenshot, or visual regression tests.
- No custom CTk color theme JSON files beyond what CustomTkinter provides out of the box.
- No new domain vocabulary — `CONTEXT.md` is unchanged.
- No new ADRs — the existing ADRs (0001 no-sync, 0002 standalone-Octopus, 0003 stock-sheet-round-trip) are not contradicted by a visual migration.
- No changes to the CSV export format or the Stock sheet round-trip.

## Further Notes

- The existing canonical spec (`.scratch/dbsbs-pos/spec.md`) and Stock sheet spec (`.scratch/stock-sheet/spec.md`) remain authoritative for all functional behavior. This spec is purely about the visual/UI layer and the deployment glue for the new dependency.
- ADRs 0001 (no in-app sync), 0002 (standalone Octopus), and 0003 (stock sheet round-trip) all stand and are not contradicted.
- The "zero external dependencies" property is relaxed to "one external dependency (`customtkinter`), managed by the startup script." This is the minimal relaxation — no other packages are introduced.
- The migration is low-risk because the UI layer is untested by design and the facade contract is unchanged. A regression in the UI cannot affect the tested domain logic. The risk is purely visual: a widget might render incorrectly or a layout might break, which is caught by manual verification.
- The startup script is the critical new piece. It must handle three scenarios cleanly: (a) dependency present → launch immediately, (b) dependency missing + internet available → install then launch, (c) dependency missing + no internet → clear error message. Scenario (c) should never happen on event day if the organizer ran the script once before the event.
- The Treeview restyling is the most technically nuanced part: `ttk.Style` configuration for Treeview headers and rows differs between Windows ttk themes, and the colors must be refreshed when the appearance mode changes. This is the one area where manual testing across light and dark mode is essential.
