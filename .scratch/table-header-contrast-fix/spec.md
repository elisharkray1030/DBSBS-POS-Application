# Spec: Dark-mode table header contrast fix

> Feature spec, published by `/to-spec`.
> **Status: done**
>
> Amends the visual layer of `.scratch/customtkinter-ui/spec.md` — no functional change to sales, settlement, catalog, or export. All vocabulary follows `CONTEXT.md`; ADRs 0001 (no in-app sync), 0002 (standalone Octopus), and 0003 (Stock sheet round-trip) stand and are not contradicted.
> Covers only the shared table styling used across the stall's two Devices.

## Problem Statement

When the stall's Device follows the Windows dark appearance, the cashier cannot read the column headings of the data tables. The header row of the Items table (Item ID, Item, Price, Remaining, Status) and the Current sale table (Item, Qty, Total) on the sale screen render as near-white text on a near-white background — effectively invisible. The same failure appears in the Sales dialog's Recorded sales table (Seq, Time, Status, Total) and in the three tables on the End of day screen (Items sold, Voids, Cash adjustments). The cashier must be able to scan headings quickly during busy selling, corrections, voids, and reconciliation, but today the headings disappear in dark mode and are weak in light mode. The rest of the app — row data, selection highlight, sold-out dimming, settlement controls, and the top summary line (Device name, Takings, Sales count) — remains legible; only the heading bar is broken.

## Solution

Fix the shared table header styling so headings are legible in both appearances with a single source of truth. Keep the six `ttk.Treeview` tables (retained because CustomTkinter has no native table) and keep their use inside CustomTkinter frames; change only the centralized header palette and the ttk theme that actually respects heading colors on Windows. Light appearance stays a pale header background with a very dark foreground; dark appearance becomes a dark header background with white foreground — both chosen to exceed WCAG AA contrast (≥4.5:1) against the header background and to remain distinct from the table body background. Apply the same fix to every heading instance: Items and Current sale on the sale screen, Recorded sales in the Sales dialog (including when opened via Correction flow), and Items sold / Voids / Cash adjustments on the End of day screen. Dialogs pick up the correct colors on creation; the main sale screen reapplies colors when the OS appearance changes while the app is running. No per-dialog overrides, no new widgets, no domain or persistence change.

## User Stories

1. As a cashier on a Device in dark mode, I want the Items table header (Item ID, Item, Price, Remaining, Status) to be clearly readable, so that I can find an Item by scanning its column during a busy sale.
2. As a cashier on a Device in dark mode, I want the Current sale table header (Item, Qty, Total) to be clearly readable, so that I can confirm what the customer is buying and the running total before settlement.
3. As a cashier, I want the same headers to remain clearly readable in light mode, so that the fix does not trade one illegible appearance for another.
4. As a cashier, I want the Items header to stay distinct from the table body (not blend into the rows), so that I can visually separate the heading bar from Item rows.
5. As a cashier, I want the Current sale header to stay distinct from its rows, so that the heading bar does not disappear against the sale lines.
6. As a cashier, I want the selected row highlight in the Items table to remain obvious after the fix, so that I know which Item will be added to the sale or marked sold-out.
7. As a cashier, I want sold-out Items to remain dimmed and distinguishable after the fix, so that I do not accidentally add an unavailable Item to a sale.
8. As a cashier correcting a Sale, I want the Sales dialog's Recorded sales header (Seq, Time, Status, Total) to be readable in dark mode, so that I can locate the Sale to correct or void by Sequence number.
9. As a cashier correcting a Sale, I want that same Recorded sales header to be readable in light mode, so that corrections work regardless of the Device's appearance.
10. As a cashier, I want the selection highlight in the Recorded sales table to remain obvious, so that I know which Sale the Correct and Void buttons will act on.
11. As a cashier reconciling at End of day, I want the Items sold header (Item, Sold) to be readable in dark mode, so that I can compare per-Item sold counts against the physical count on the table.
12. As a cashier reconciling at End of day, I want the Voids header (Seq, Time, Total) to be readable in dark mode, so that I can audit which Sales were voided and excluded from takings.
13. As a cashier reconciling at End of day, I want the Cash adjustments header (Amount, Reason, Time) to be readable in dark mode, so that I can verify Cash added or removed mid-day against Expected cash.
14. As a cashier reconciling at End of day, I want all three End of day headers to be readable in light mode as well, so that reconciliation is legible on either appearance.
15. As a cashier, I want the heading style to be consistent across the four surfaces (Items, Current sale, Sales dialog, End of day), so that the app feels like one cohesive stall app rather than four different looks.
16. As a cashier, I want the header text to stay a consistent weight and size after the fix, so that readability improves without changing the information density of the 30–40 Item Catalog.
17. As a cashier, I want the fix to survive an OS appearance change while the app is running (e.g., Windows toggled from light to dark between sales), so that headings do not revert to invisible until restart.
18. As a cashier, I want dialogs opened after an appearance change to show the new appearance's headings, so that a Sales or End of day view opened mid-event is never illegible.
19. As a cashier, I want open dialogs to not be required to repaint instantly on a mid-sale appearance toggle, so that the common fete scenario (no toggle mid-transaction) stays simple and robust.
20. As the organizer, I want the fix to be centralized (one palette/style definition) rather than patched per screen, so that future heading changes do not drift between Devices or require per-dialog edits.
21. As the organizer, I want the fix to preserve the app's offline, double-clickable deployment (no new dependencies, no network, no installer), so that both Devices still launch from a copied folder.
22. As the organizer, I want the fix to preserve the existing Catalog, Sale, Cash adjustment, Correction, Void, Expected cash, Float, Device name, and Sales export behavior, so that takings, Octopus totals, and Stock sheet reports combine exactly as before.
23. As a developer, I want the domain glossary (Item, Item ID, Sale, Cash, Octopus, Voucher, Catalog, Stock sheet, Device, Float, Correction, Void, Expected cash, Cash adjustment, Sales export, Device name, Split settlement, Sequence number) to remain unchanged, so that the codebase vocabulary stays stable and no new glossary terms are introduced for a purely visual bug.
24. As a developer, I want the fix to keep the UI layer untested by design except for the smallest guard that prevents regression, so that the existing facade test suite remains the bulk of the safety net.
25. As a developer, I want the header colors to be defined alongside the existing body/select/sold-out colors in one palette, so that light and dark appearances are reasoned about together.

## Implementation Decisions

- **Scope — what is fixed and where**: every `ttk.Treeview` column heading row. That is exactly six logical tables across four surfaces, all sharing one styling path: sale screen — Items table (Item ID, Item, Price, Remaining, Status) and Current sale table (Item, Qty, Total); Sales dialog — Recorded sales table (Seq, Time, Status, Total) used for Correction and Void; End of day screen — Items sold table (Item, Sold), Voids table (Seq, Time, Total), Cash adjustments table (Amount, Reason, Time). No fix to the top status bar (Device name / Takings / Sales count), section labels ("Items", "Current sale"), or row data — those are already legible.

- **Single source of truth**: keep the existing shared styling module as the only place that defines table colors and heading configuration. All tables are created via the shared table factory; no per-screen or per-dialog heading override is introduced. This preserves the CustomTkinter migration decision from the UI spec (Treeview retained and restyled via `ttk.Style`) and avoids drift between the sale screen, Sales dialog, and End of day screen.

- **Palette decision**: continue defining a light palette and a dark palette, each with body background/foreground, field background, selection colors, sold-out color, and header background/header foreground. Chosen values — light header background pale `#dbe4ee` with foreground very dark slate `#0f172a`, dark header background `#333333` with foreground white `#ffffff` — are carried from the grilling consensus. Both exceed WCAG AA (≥4.5:1) for header foreground vs. header background (light ~13.9:1, dark ~12.6:1) and keep the header bar visibly distinct from the body background (light body white vs. pale blue, dark body `#242424` vs. `#333333`).

- **Root-cause mechanism — ttk theme**: on Windows the default `vista` ttk theme ignores `Treeview.Heading` background/foreground, which is why the palette set in `ttk.Style` had no effect and headings rendered white-on-white. The fix switches the style's theme to `clam`, a theme bundled with Tk 8.6 that respects heading colors in both appearances. The theme switch is performed centrally, inside the same routine that configures heading and row styles, with a safe fallback if the theme is unavailable. The visual side-effect (slightly flatter ttk rendering) is accepted as minimal and preferable to replacing Treeview with a custom widget, which was explicitly out of scope in the UI spec and rejected during grilling.

- **Configuration ordering**: theme selection happens before any heading/row configuration, because switching themes resets style definitions. After the theme is set, the shared routine configures the Treeview row style (font, row height, body/field background, body foreground, border) and maps selection colors, then configures `Treeview.Heading` (bold header font, header background, header foreground) and maps the active-state heading colors to the same values (so hover does not wash out the heading). This ordering guarantees the requested header colors are actually applied on Windows.

- **Appearance adaptation**: the existing appearance watcher that polls the CustomTkinter appearance mode and reapplies table styling when the OS setting changes is retained. When a change is detected, the shared style configuration is re-run (which re-selects the theme and reapplies the now-correct palette) and the sold-out row tag is refreshed for the sale screen's Items table. Dialogs are not required to repaint live while open; they are constructed after the style has been updated and therefore show the correct appearance on next open — the fete's Devices are not toggled mid-transaction in practice.

- **Sold-out and selection preservation**: the dimmed sold-out tag and the accent-colored selection mapping are unchanged in semantics — only re-asserted after each appearance re-apply so they do not get lost when the theme resets styles.

- **No domain / persistence / export / vocabulary change**: the Catalog remains read-only from the Stock sheet, Sales keep their Sequence number and timestamp, settlement rules (Octopus settles full Sale, Cash + Voucher may split) are untouched, Corrections count toward totals and Voids stay in the audit section, Expected cash computation and Sales export shape are unchanged, and no terms are added to the project glossary — consistent with the grilling outcome that "appearance mode" and "header" are UI implementation details not domain language. No architecture decision record is needed; the change is a reversible bug fix, not a hard-to-reverse trade-off.

## Testing Decisions

- **What makes a good test here**: tests assert externally observable behavior — that the shared palette exposes high-contrast heading colors for both appearances and that the shared styling routine arranges for the heading style to carry those colors — not the internal widget hierarchy of any screen or dialog. A refactor that moves the decorator from one screen to another, or renames a widget variable, must not break tests; a regression that reintroduces invisible headings must break tests.

- **Chosen seams — highest possible, fewest possible**:
  - **Primary seam (new, highest available for this visual bug): the shared styling module's palette and style configuration**. The palette accessor (returns the light/dark color map for the active appearance) and the routine that configures ttk heading/row styles are the natural seams because every table in the app funnels through them. Existing seams sit lower (the `PosSession` facade) and cannot observe heading colors at all, which is why a narrow, focused seam above the facade is warranted here. Ideal count is one module seam; a second function within the same module (palette vs. style application) is acceptable if needed but not a separate cross-module seam.
  - **Why not the facade**: the `PosSession` facade — the canonical seam for the bulk of the app — is exercised by the existing 13-file suite and is deliberately UI-agnostic. It cannot see ttk heading colors, so adding a facade-level test for contrast would be an implementation-detail leak. The facade suite stays green as a regression guard that the fix did not touch domain, persistence, or export, but it is not the seam for this feature.
  - **Why not per-screen seams**: Sale screen, Sales dialog, and End of day screen are not seams today (UI layer is untested by design) and should not become seams for a single palette bug — that would multiply seams and couple tests to layout. The single shared module seam covers all four surfaces at once.

- **Modules under test**: only the shared styling module (palette and heading/row style application). Out of test: the facade, domain logic, catalog loader, persistence, export, and individual screens/dialogs — consistent with the UI spec's decision that the UI layer is untested by design. The only exception to "no UI tests" is this narrow styling guard.

- **Prior art and test style**:
  - The existing test suite is prior art for facade-level behavior: fixtures use `InMemoryPersistence` behind `PosSession`, drive sale building, settlement, correction, void, sold-out, cash adjustments, running summary, end-of-day figures, and CSV export shape. None of those tests change; they remain the regression net that proves the header fix is purely visual.
  - No prior art exists for UI palette testing in this repo. The new tests follow the existing conventions where they apply: plain `pytest` functions, no mocking of business logic, assertions on returned values or style state, not on widget object identity. They mirror the SQLite round-trip sanity test's spirit — a tiny, focused check that real toolkit state matches expectations.

- **Validation mix (not just automated)**:
  - Automated: palette accessor returns the locked heading pairs for both appearances (light `#dbe4ee`/`#0f172a`, dark `#333333`/`#ffffff`) and that both pairs exceed 4.5:1 contrast; style configuration, after being invoked for each appearance, leaves `Treeview.Heading` background/foreground queryable as those values and leaves the theme set to one that respects headings.
  - Manual (authoritative for a visual bug): on Windows, launch the app, verify Items and Current sale headers legible in dark, toggle OS to light and verify again, open Sales dialog and End of day screen and verify their table headers in both appearances, and verify selection highlight and sold-out dimming still work. The automated palette guard prevents silent regression; the manual pass proves human legibility.

## Out of Scope

- Replacing `ttk.Treeview` with a CustomTkinter table or any other widget — Treeview stays, restyled, as decided in the UI spec.
- Redesigning the overall light/dark color system, adding new themes, or adding per-dialog custom palettes — only the header foreground/background are tightened; the broader CTk theme stays as provided.
- Reworking the top summary bar (Device name / Takings / Sales count) or section labels — legible as-is.
- Live repaint of already-open dialogs on appearance change — dialogs show the new appearance on next open, which matches actual fete use.
- Any change to Catalog loading, Sale building, settlement rules, change computation, Sequence numbers, Corrections, Voids, Cash adjustments, Expected cash, Sales export, Stock sheet round-trip, Device name handling, or wipe — strictly visual.
- Adding glossary entries or architecture records for this fix — no new domain language, no hard-to-reverse decision.
- Automated screenshot or visual-regression tests, high-contrast/OS accessibility modes, or high-DPI scaling changes beyond what CustomTkinter already provides.
- New dependencies, installers, bundlers, or deployment changes — offline double-click from a copied folder remains the delivery model.
- Data migration or schema change — none.

## Further Notes

- This spec is a narrow visual patch on top of the UI migration; the canonical spec and Stock sheet spec remain authoritative for all functional behavior. The fix restores the intent of the UI spec's decision that "Treeview headers use the app's color theme" — the `vista` theme was silently defeating that intent on Windows.
- The contrast targets encode a design invariant: heading text must remain legible against its own bar and the bar must remain distinguishable from the body. If future palettes change, both invariants should be re-checked in both appearances, not just one.
- The `clam` theme choice is the least invasive way to make heading colors stick on Windows. A future alternative (e.g., a CustomTkinter table widget if upstream adds one) could revisit this, but for the fete's two offline Devices, the current fix is the lowest-risk path.
- Grilling consensus (four rounds, all "as you stated") locked the palette values, the single-source approach, the root-cause theme switch, the no-live-dialog-repaint scope, and the no-glossary/no-ADR outcome — this spec records that consensus.
