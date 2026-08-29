# DBS Garden Fete — Offline POS Application Plan

> **SUPERSEDED.** This early planning document describes a Flask + SQLite web
> app that was never built. The shipped product is a **CustomTkinter desktop
> POS** for Windows. The canonical spec lives at GitHub issue #32, the domain
> glossary at `CONTEXT.md`, decisions in `docs/adr/`, and run/deploy steps in
> `README.md`. Kept below as history of the decision process.

**Team:** 3 people · **Venue:** DBS Garden Fete (1 stall) · **Devices:** 2 laptops (1 stall, same catalog) · **Payments:** cash + Octopus — but money is handled separately, outside the app · **Deadline:** 2026-10-31 · **Constraint:** $0/mo, fully offline, venue may have NO Wi-Fi · **Status:** Superseded — see the banner above

---

## Executive Summary

1. **Verdict:** build a small local web app — Flask + SQLite, run on **one laptop**. The second laptop is a browser client that joins over a hotspot **only if the venue allows one** (v1, not MVP). The MVP must run with zero network at all.
2. **What it actually is:** a **stock-and-price notebook with a fast sale logger**. The app notes catalog, prices, and stock; records every sale with time, items, and payment method as an in-system log. **The money itself is counted separately by the team** — the app never reconciles a drawer or touches Octopus/cash handling.
3. **Core loop:** import the catalog CSV once → sell all day against one local database → at close, one button gives per-item sold counts, totals by payment method (informational), and a CSV export of the day.
4. **Stack:** Flask + SQLite + vanilla browser UI (no build step). Python is the team's proven toolkit (Lateness app is the same shape). No Docker, no hosting, no accounts. Bare `python app.py`.
5. **Cost:** $0. Runs on hardware the team already brings. No cloud, no subscriptions, no per-transaction fees — and nothing to break when the venue has no internet.
6. **Effort:** MVP ~16–20h · v1 ~+6–8h · total ~22–28h. Deadline 2026-10-31 ≈ 10 weeks at ~3h/week. Comfortable, with a rehearsal before the fete.
7. **Receipts:** not required. The sale log **is** the receipt book — every sale viewable in the system, filterable by time/items/method. Optional browser-print stays in v2 if anyone ever wants paper.
8. **De-risk first:** get a real sample catalog CSV when the team has one (contract stays provisional until then), and check whether a laptop hotspot works at the venue (decides if LAN mode ever ships).
9. **Confidence: 0.9.** Scope is now small and unambiguous. Remaining variance: CSV format details (Q4) and hotspot feasibility (Q6) — each moves it ±0.05.

---

## 1. Strategy

### 1.1 Build vs configure — honest assessment

| Need | Spreadsheet | Commercial POS | Custom local app (this plan) |
|---|---|---|---|
| Works with zero internet | ✅ | ⚠️ offline ones need accounts/setup; online ones dead | ✅ by design |
| CSV catalog import | ⚠️ manual | ⚠️ data entry or paid import | ✅ native |
| Record sales with method (cash/Octopus) | ⚠️ manual | ✅ (but tied to payment integrations) | ✅ as a log field — money handled separately |
| Live shared state across 2 laptops | ❌ two copies, merge by hand | ✅ (but online) | ✅ LAN mode (v1, hotspot-gated) |
| End-of-day totals + per-item counts | ⚠️ hand formulas | ✅ | ✅ built-in |
| Cost | $0 | paid monthly + terminal fees | $0 |
| Team already knows the stack | — | — | ✅ (Lateness app pattern) |

**Verdict:** a tiny build still beats configuration — the corner (offline, CSV, $0, money handled outside) has no commercial product in it, and the build is mostly the sell-screen UI. Note the deliberate simplification: because money is handled separately, we are NOT building payment capture, reconciliation, or Octopus integration at all.

**Anti-patterns rejected:**
- No cloud POS / SaaS of any kind — venue has no guaranteed internet.
- No payment/reconciliation features — the team counts money separately; the app logs, it doesn't balance.
- No desktop app (Tauri/Electron/installer) — a browser UI on localhost has zero install friction.
- No PWA/service-worker sync — backwards for us. Offline-first means the server IS local.
- No multi-device sync in MVP — one laptop is the default; the second joins only if a hotspot works.

### 1.2 MVP scope

The MVP is a **single-laptop, zero-network sale logger**:

1. `Catalog in from CSV` — import a CSV (name, price, stock, category) with validation; errors reported per line, nothing half-imported.
2. `Sell fast` — big-button catalog grid, tap to add to cart, running total, choose **cash** or **Octopus** (informational), complete. Sub-5-second sale.
3. `Stock that stays honest` — stock decrements on every sale; "0 left" warning; restock by editing or re-importing.
4. `The receipt book` — every sale is logged in-system: time, items, quantities, unit prices, total, payment method. Filterable, never deleted.
5. `Close the day` — summary: revenue by payment method, per-item quantities, stock deltas, plus a CSV export of the whole day. Informational — the team's money count happens separately.
6. `Survives no internet` — every asset bundled locally; Wi-Fi off, hotspot off, router dead — the app never notices.

### 1.3 User stories (MVP)

- As a stall operator, I want to import the team's catalog CSV once so I never type prices at the fete — errors reported per line.
- As a stall operator, I want to complete a sale in under 5 seconds with a big-button grid, so queues don't build — pick items, total, pick cash/Octopus, done.
- As a stall operator, I want stock to decrement automatically and warn me at zero, so I never sell what we don't have.
- As the team lead, I want every sale recorded in the system — time, items, method — so the log is our receipt book and disputes resolve in seconds.
- As the team lead, I want an end-of-day summary: per-item sold counts, cash vs Octopus split, stock deltas — so the (separate) money count has a checklist to compare against.
- As the team lead, I want the day's sales exported to CSV, so records land in the team's usual format.
- As anyone at the stall, I want the app to work with no internet at all — it must never depend on the cloud, the venue, or anything external.

### 1.4 Explicit assumptions

- **A1 ✅ RESOLVED — both devices are laptops.** Same form factor; no touch-target special-casing needed.
- **A2:** One stall, one catalog. **MVP runs on one laptop**; the second laptop joins via browser over a hotspot only if the venue allows one (Q6) — v1, not MVP.
- **A3 (provisional):** Catalog = CSV with at least name, price, stock, category. Contract stays provisional until the real sample arrives (Q4).
- **A4 ✅ RESOLVED — money is handled separately.** The app records the payment method as a log field for stats; it does not capture, reconcile, or integrate payments.
- **A5 ✅ RESOLVED — the fete is one day.** A `day` column on every sale keeps multi-day free anyway.
- **A6 ✅ RESOLVED — no printed receipts.** The in-system sale log is the receipt book. Browser-print is optional v2.
- **A7 (default):** A sale, once completed, stands. Void/refund is v1 and only if the team wants it (Q5 — default no).
- **A8:** Prices are HKD with up to 2 decimals; the UI shows `$X.XX`; stored as integer cents.

---

## 2. Solution Design

### 2.1 Delivery vehicle — trade-off table

| Option | Cost | Offline? | Friction removed? | Verdict |
|---|---|---|---|---|
| **Local Flask app (picked)** | $0 | ✅ native | CSV import, fast sales, built-in log + day close | ✅ **Recommend** |
| Spreadsheet + hand-entry | $0 | ✅ | None — the pain is the math and the manual log | Fallback if build fails |
| Offline-capable commercial POS | paid | ⚠️ | Setup/account/terminal fees; payment features we don't need | Rejected (cost + fit) |
| Cloud POS (Square/iCHEF) | paid | ❌ | — | Rejected (needs internet) |
| Desktop app (Electron/Tauri) | $0 | ✅ | None over browser UI; adds install friction | Overkill |

### 2.2 Core loop (the whole product in one sentence)

> Once: import the catalog CSV. All day: sell against one local database — the second laptop joins only if a hotspot works. At close: one button shows per-item counts, the cash/Octopus split, and exports the day's CSV.

### 2.3 Receipts — resolved

- **No printing.** The sale log screen is the receipt book: every sale with time, items, unit prices, total, and method; filterable; nothing ever deleted.
- Optional browser-print of a sale (any printer) is parked in v2 — only if the team asks for paper.

---

## 3. Software Stack (all free, all local — nothing to verify)

| Layer | Choice | Why |
|---|---|---|
| Web framework | **Flask** | Proven in this team (Lateness app). Tiny, no magic. |
| Database | **SQLite** (WAL mode) | Zero-ops single file; plenty for a stall's volume. |
| Frontend | **Vanilla HTML/CSS/JS**, bundled locally | No build step, no CDN — works with Wi-Fi fully off. |
| CSV | Python `csv` stdlib | Import catalog, export day's sales. |
| Serving | Laptop A hosts on `127.0.0.1:5000` (MVP) · `0.0.0.0:5000` when LAN mode is on (v1) | Second laptop never needs Python — just a browser. |
| Python env | System Python or the repo's venv on the host laptop only | — |
| Docker | Optional, not required | Bare `python app.py` is simpler at a venue. |

**Rejected:** anything requiring an account, a cloud, or connectivity (Supabase, Vercel, Workers, managed DBs — all online by nature). Local-first is the whole point.

---

## 4. Architecture

### 4.1 Diagram

```
MVP — zero network needed:
  Laptop A (host)
    Flask app + SQLite (catalog, sales, stock)  →   browser UI on localhost:5000
    binds 127.0.0.1:5000 — no Wi-Fi, no router, no internet required

v1 LAN mode (only if the venue allows a hotspot):
  Laptop A (host)  ── local hotspot / Wi-Fi ──►  Laptop B (browser only)
    binds 0.0.0.0:5000                            opens http://<A's-IP>:5000
    same catalog, same sales, live

Day close (on the host): summary screen (per-item, per-method) → CSV export → done
```

### 4.2 Data model (SQLite)

```sql
CREATE TABLE products (            -- imported from CSV; restock = edit or re-import
  id          INTEGER PRIMARY KEY,
  name        TEXT NOT NULL UNIQUE,
  price_cents INTEGER NOT NULL,    -- HKD, stored as cents, no float math
  stock       INTEGER NOT NULL DEFAULT 0,
  category    TEXT DEFAULT '',
  active      INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE sales (               -- the receipt book — one row per completed sale
  id          INTEGER PRIMARY KEY,
  day         TEXT NOT NULL,       -- 'YYYY-MM-DD' local date
  ts          TEXT NOT NULL,       -- ISO local time
  method      TEXT NOT NULL,       -- 'cash' | 'octopus' — informational only
  total_cents INTEGER NOT NULL,
  device      TEXT NOT NULL DEFAULT 'A'   -- which laptop took it (v1 LAN mode)
);

CREATE TABLE line_items (
  id          INTEGER PRIMARY KEY,
  sale_id     INTEGER NOT NULL REFERENCES sales(id),
  product_id  INTEGER NOT NULL REFERENCES products(id),
  qty         INTEGER NOT NULL,
  unit_cents  INTEGER NOT NULL,    -- price at time of sale (snapshot)
  line_cents  INTEGER NOT NULL
);
CREATE INDEX idx_sales_day ON sales(day);
```

Design notes:
- **Prices as integer cents** — no floating-point money, ever.
- **Unit price snapshotted** on the line item — a later price change never rewrites history.
- **Stock is live**: decrement on sale; warning at 0, not a hard block (staff can restock mid-day).
- A `day` column on every sale keeps the model multi-day-ready even though the fete is one day (A5).
- **No payment tables, no reconciliation tables** — money is handled separately (A4). `method` is a label, not a ledger.

### 4.3 Catalog CSV contract (provisional — pending the real sample, Q4)

```csv
name,price,stock,category
Hot Dog,20,50,Food
Chocolate Milk,12,40,Drinks
```

- `price` in HKD (whole dollars or decimals — parsed to cents).
- Import is all-or-nothing per file: validation pass first, then apply. Errors name the line and column.
- Re-importing updates prices/stock for existing names and adds new ones.

### 4.4 Core flows

**Import catalog** (before the fete, or at open)
1. Operator picks the CSV → validation pass → errors listed per line → apply on confirm.
2. Summary of what changed: N new, M updated, K errors (none applied).

**Sell** (the main screen)
1. Catalog grid: category filter tabs + big item buttons showing name and price; stock shown, zero-stock items greyed with "0 left".
2. Tap items → cart on the right: qty steppers, running total.
3. **Pay**: one tap for Cash, one for Octopus → sale recorded, stock decremented, cart clears. Done in one screen — no confirm dialogs.

**Sale log** (the receipt book)
- Table of every sale: time, items (with qty × unit price), total, method. Filters by day and method; nothing is ever deleted.

**Close the day** (at the end)
1. "Close day" → summary: revenue cash / revenue octopus / total; per-item quantities; stock deltas (sold per item).
2. These are **informational** — the team's money count happens separately (A4). The summary doubles as a checklist for that count.
3. Export: `sales-YYYY-MM-DD.csv` (per sale: time, items, method, total) + the summary on screen.

**Void / refund** (v1, only if wanted — Q5, default no)
- Last-sale undo within a day: flags the sale as voided (kept in the log, excluded from totals), stock restored.

### 4.5 Concurrency & the LAN edge

- **MVP: no concurrency.** One laptop, one process, one browser. SQLite WAL is still on for crash-safety.
- **v1 LAN mode:** if the venue allows a hotspot, laptop B is a browser client on the same DB — WAL + short transactions handles a stall's few-transactions-per-minute easily. Per-sale `device` tag keeps the log truthful.
- If LAN mode is never used (no hotspot), nothing is lost — the MVP is complete without it.

---

## 5. Roadmap

### Phase 0 — Validate before building (1–2h, this week)
- Get a **real sample catalog CSV** when the team has one (Q4) — it locks the import contract.
- Check whether a **laptop hotspot is allowed at the venue** (Q6) — decides whether LAN mode ever ships.
- Confirm void/refund isn't needed at the fete (Q5 — default: not needed).

### Phase 1 — MVP (~16–20h)
Scope: CSV import with validation · sell screen (grid, cart, cash/Octopus) · stock decrement + zero warnings · sale log screen (the receipt book) · SQLite schema above · single-laptop offline mode (binds localhost only) · day close (summary, per-method totals, CSV export) · bundled local assets (zero internet).
Acceptance:
- A 50-item catalog imports in one step with per-line errors; re-import updates cleanly.
- A sale (3 items, cash) completes in under 5 seconds from item tap to total.
- Stock matches hand-count after 20 mixed test sales; zero-stock items can't be added to cart.
- Every sale appears in the log with items, unit prices, method, and time; the log survives an app restart.
- Day close totals match a hand count; CSV export opens cleanly in Excel.
- **Wi-Fi fully off, no network adapters, no router** — the app sells end-to-end. Verify: no CDN requests in devtools, `localhost` only.

### Phase 2 — v1 (+6–8h, hotspot-gated)
Scope: LAN mode (host binds `0.0.0.0`, laptop B joins by URL) · void/refund (flagged, not deleted) · product quick-edit (price/stock) · low-stock alert at a threshold · nicer touch styling.
Acceptance:
- Laptop B on the hotspot sees every sale from A and can sell simultaneously; totals reconcile.
- Void restores stock and excludes the sale from totals; the log still shows it.
- A sale on B is tagged with device B in the log.

### Phase 3 — v2 (optional, +4–6h, only if the team asks)
Scope: browser-print of a sale/receipt · printable price list from the catalog · multi-day log view · barcode scan (USB scanner types the product code — needs codes in the CSV, Q4 extension).

**Total effort: 22–28h** to a complete, rehearsed system. Cost: $0. Maintenance: none (local app; the repo is the backup).

---

## 6. Risks & Gotchas

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Venue has no Wi-Fi** | medium | ~~High~~ → **None for MVP** | MVP binds localhost only and needs zero network. LAN mode (v1) is hotspot-gated and optional. |
| **CSV doesn't match the assumed format** | near-certain (first time) | Medium | Phase 0: real sample file locks the contract before the importer is written. Errors report line+column. |
| **Money-count mismatch at close** | medium | Medium | The app is explicitly *informational* — the team counts separately (A4). Day-close summary doubles as the checklist, so a mismatch is caught at the fete, not after. |
| **Floating-point money bugs** | certain if careless | Medium | Prices stored as integer cents; no float arithmetic anywhere. |
| **SQLite corruption (power cut)** | low | Medium | WAL mode; small data; CSV export at close is the backup. |
| **Scope creep (receipts, barcodes, LAN)** | medium | Low | Everything beyond §5 Phase 1 is v1/v2 and gated on rehearsal time or an explicit ask. |
| **Team doesn't rehearse** | medium | High | Phase 0 ends with a 1-hour dry run: real catalog, 20 fake sales, day close. The fete is not the first run. |
| **Price changes mid-day** | medium | Low | Quick-edit (v1); unit price snapshotted on line items, so history stays true. |

---

## 7. Effort summary

| Phase | Hours | Window |
|---|---|---|
| Phase 0 — validate | 1–2h | this week |
| Phase 1 — MVP | 16–20h | by end of September (dry-run-able) |
| Phase 2 — v1 | 6–8h | October, before rehearsal |
| Phase 3 — v2 (optional) | 4–6h | only if time remains or the team asks |
| Rehearsal | 1h | the week before the fete |

Deadline 2026-10-31 leaves ~2 weeks of buffer after v1 for real-world fixes.

---

## 8. Open Questions

1. ✅ **RESOLVED — both devices are laptops.** Same form factor, no touch special-casing.
2. ✅ **RESOLVED — no printed receipts.** The in-system sale log is the receipt book. Browser-print parked in v2.
3. ✅ **RESOLVED — money is handled separately.** The app records method as an informational log field only; no payment capture or reconciliation. (Reader hardware is the team's business, not the app's.)
4. ⏳ **PENDING — real catalog CSV sample.** The import contract above is provisional until the actual file arrives. Nothing blocks Phase 1 except locking the column order.
5. ⏳ **PENDING (default no) — void/refund at the fete?** MVP records only; void is v1 if the team wants it.
6. ⏳ **PENDING — is a laptop hotspot allowed at the venue?** No → single-laptop MVP forever (fully sufficient). Yes → LAN mode ships in v1.
7. ✅ **RESOLVED — the fete is one day.** `day` column keeps multi-day free anyway.

---

## Appendix — Why no "verified sources" section

Unlike the Scheduler plan (which had to verify Cloudflare/Telegram free tiers), this app is **100% local** — Flask, SQLite, and a browser are already in the team's proven toolkit (the Lateness app runs the same stack). There are no free-tier limits to verify because there is no third-party service in the critical path.

*Confidence: overall 0.9. Remaining variance: Q4 (CSV format details) and Q6 (hotspot feasibility) — each moves it ±0.05.*

---

## Update log
- 2026-08-15: Initial plan. Requirements from Elijah: CSV catalog, 2 laptops at 1 stall, fully offline, cash + Octopus, deadline end of October. Plan written as a standalone file per instruction — existing repo files untouched.
- 2026-08-15 (2nd): Open questions resolved — both devices are laptops (Q1); no printed receipts, in-system sale log instead (Q2); **money handled separately** — app logs method, never reconciles (Q3); fete is one day (Q7). Consequence: MVP is single-laptop, zero-network; LAN mode moved to v1, hotspot-gated. Sale log promoted into MVP scope. Reconciliation features dropped. Effort 22–28h, confidence 0.9. Pending: CSV sample (Q4), hotspot check (Q6), void/refund confirm (Q5).
