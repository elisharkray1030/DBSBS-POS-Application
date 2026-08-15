# DBS Garden Fete — Offline POS Application Plan

**Team:** 3 people · **Venue:** DBS Garden Fete (1 stall) · **Devices:** 2 laptops at the stall · **Payments:** cash + Octopus · **Deadline:** 2026-10-31 · **Constraint:** $0/mo, fully offline · **Status:** Decision-ready, pending open questions in §8

---

## Executive Summary

1. **Verdict:** build a small local web app — Flask + SQLite, run on a laptop, second laptop joins over local Wi-Fi. Do NOT buy a cloud POS. The offline constraint alone disqualifies every online POS (Square, Shopify, iCHEF), and the CSV catalog + Octopus recording + $0 rule rule out the offline-capable commercial ones.
2. **Why offline-first:** the fete venue can't be relied on for internet. The app must run with zero connectivity — all assets bundled locally, no CDNs, no accounts, no cloud calls anywhere in the happy path.
3. **Core loop:** import the catalog from CSV once → sell all day on 2 laptops against shared state → close the day: summary + CSV export for the team's records.
4. **Stack:** Flask + SQLite + vanilla browser UI (no build step). Python is already the team's proven toolkit — the Lateness app is the same shape (Flask + SQLite + CSV). No Docker needed at the venue; bare `python app.py`.
5. **Cost:** $0. Runs on hardware the team already brings. No hosting, no subscriptions, no per-transaction fees.
6. **Effort:** MVP ~20–24h · v1 ~+6–10h · total ~26–34h. Deadline is 2026-10-31 — about 10 weeks at ~3–4h/week. Comfortable, with a full rehearsal before the fete.
7. **Octopus is recorded, not integrated:** the Octopus card reader is standalone hardware that takes payment itself; the app only records "Octopus $X" as the payment method. No SDK, no merchant integration. (Confirm the reader exists — Q3.)
8. **De-risk first:** confirm the open questions (§8), get a real sample catalog CSV, and run a one-hour dry rehearsal with both laptops before writing polish features.
9. **Confidence: 0.85.** The build is small and the pattern is already proven in this team. Remaining variance: second-device form factor (Q1), Octopus hardware (Q3), venue network (Q6).

---

## 1. Strategy

### 1.1 Build vs configure — honest assessment

| Need | Spreadsheet | Commercial POS | Custom local app (this plan) |
|---|---|---|---|
| Works with zero internet | ✅ | ⚠️ offline-capable ones need accounts/setup; online ones dead | ✅ by design |
| CSV catalog import | ✅ | ⚠️ manual data entry or paid import | ✅ native |
| Cash + Octopus recording | ⚠️ manual | ⚠️ Octopus needs merchant integration, usually paid | ✅ record method + amount |
| 2 devices, shared live state | ❌ two copies, merge by hand | ✅ (but online) | ✅ LAN shared DB |
| End-of-day totals + cash reconciliation | ⚠️ hand formulas | ✅ | ✅ built-in |
| Cost | $0 | paid monthly + per-terminal fees | $0 |
| Team already knows the stack | — | — | ✅ (Lateness app pattern) |

**Verdict:** a tiny build genuinely beats configuration here. The requirements (offline, CSV, cash + Octopus, $0) form a corner no free product sits in. The build is small enough that the effort is mostly the sell-screen UI, not plumbing.

**Anti-patterns rejected:**
- No cloud POS / SaaS of any kind — the venue has no guaranteed internet.
- No desktop app (Tauri/Electron/installer) — a browser UI on localhost/LAN has zero install friction; both laptops already have browsers.
- No PWA/service-worker sync — that's the *online* fallback, backwards for us. Offline-first means the server IS local.
- No Octopus SDK integration — merchant-grade integration needs an account, a terminal, and connectivity. Out of scope by definition.

### 1.2 MVP scope

The MVP is a **shared, offline sale-recording app on one stall's Wi-Fi**:

1. `Catalog in from CSV` — import a CSV (name, price, stock, category) with validation; errors reported per line, nothing half-imported.
2. `Sell fast` — big-button catalog grid, tap to add to cart, cart shows running total, choose **cash** or **Octopus**, complete. Sub-5-second sale.
3. `Stock that stays honest` — stock decrements on every sale; "0 left" warning; restock by editing or re-importing.
4. `Two laptops, one truth` — laptop A hosts the app; laptop B opens a browser to A's address on the same Wi-Fi. Both see the same catalog and sales live.
5. `Close the day` — end-of-day summary: revenue by payment method, per-item quantities, stock deltas, cash reconciliation sheet, CSV export for records.
6. `Survives no internet` — every asset bundled locally; the app runs identically with Wi-Fi off except the second laptop loses its connection (fallback in v1).

### 1.3 User stories (MVP)

- As a stall operator, I want to import the team's catalog CSV once so I never type prices at the fete — import with errors reported per line.
- As a stall operator, I want to complete a sale in under 5 seconds with a big-button grid, so queues don't build — pick items, total, pick cash/Octopus, done.
- As a stall operator, I want stock to decrement automatically and warn me at zero, so I never sell what we don't have.
- As the second operator on the same stall, I want my laptop to see the same catalog and sales as the first, so we're never double-counting.
- As the team lead, I want an end-of-day summary: cash vs Octopus totals, per-item sales, and a reconciliation sheet, so the float matches the drawer.
- As the team lead, I want the day's sales exported to CSV, so records land in the team's usual format.
- As anyone at the stall, I want the app to work even if the venue has no internet — it must never depend on the cloud.

### 1.4 Explicit assumptions (each maps to an open question)

- **A1:** The two devices are **laptops** (Q1 — form factor of device 2; tablets just mean bigger touch targets).
- **A2:** **One stall**, one point of sale, two operators. Both laptops face the same customers.
- **A3:** Catalog = CSV with at least: name, price, stock (Q4 — exact columns from a real sample file).
- **A4:** **Octopus = standalone reader** the team already has; the app records the payment method and amount only (Q3).
- **A5:** The fete is a **single day** (Q7). The data model keeps a date on every sale anyway, so multi-day costs nothing later.
- **A6:** Receipts are **not required** in MVP (Q2). Cash sales get no receipt unless a printer is decided.
- **A7:** A sale, once completed, stands. Void/refund is v1 (Q5).
- **A8:** Prices are HKD with up to 2 decimals; the UI shows `$X.XX`.

---

## 2. Solution Design

### 2.1 Delivery vehicle — trade-off table

| Option | Cost | Offline? | Friction removed? | Verdict |
|---|---|---|---|---|
| **Local Flask app (picked)** | $0 | ✅ native | Shared live state, CSV import, day close | ✅ **Recommend** |
| Spreadsheet + hand-entry | $0 | ✅ | None — the pain is the math and the merge | Fallback if build fails |
| Offline-capable commercial POS | paid | ⚠️ | Setup/account/terminal fees; Octopus integration usually extra | Rejected (cost + fit) |
| Cloud POS (Square/iCHEF) | paid | ❌ | — | Rejected (needs internet) |
| Desktop app (Electron/Tauri) | $0 | ✅ | None over browser UI; adds install friction | Overkill |

### 2.2 Core loop (the whole product in one sentence)

> Once: import the catalog CSV. All day: two laptops sell against one shared database. At close: one button prints the day's numbers and exports the CSV.

### 2.3 Receipts — where they stand

- MVP: **no receipts**. Most fete stalls don't issue them; the screen confirms the sale.
- v1 (optional): browser-print a simple receipt (works on any printer the venue has — thermal 80mm via the browser's print-to-size, or plain A4). Decide at Q2.

---

## 3. Software Stack (all free, nothing to verify — it's local)

| Layer | Choice | Why |
|---|---|---|
| Web framework | **Flask** | Proven in this team (Lateness app). Tiny, no magic. |
| Database | **SQLite** (WAL mode) | Zero-ops single file; plenty for a stall's transaction volume. |
| Frontend | **Vanilla HTML/CSS/JS**, bundled locally | No build step, no CDN — works with Wi-Fi fully off. |
| CSV | Python `csv` stdlib | Import catalog, export day's sales. |
| Serving | Laptop A hosts on `0.0.0.0:5000`; laptop B opens `http://<A's-IP>:5000` | No install on B beyond a browser. |
| Python env | System Python or the repo's venv on A only | B never needs Python. |
| Docker | Optional, not required | The Lateness app has a compose.yaml; here bare python is simpler at a venue. |

**Rejected:** anything requiring an account, a cloud, or connectivity (Supabase, Vercel, workers, managed DBs — all online by nature). Local-first is the whole point.

---

## 4. Architecture

### 4.1 Diagram

```
Laptop A (host — the only thing running Python)
  Flask app + SQLite (catalog, sales, stock)
  binds 0.0.0.0:5000
        │  local Wi-Fi (no internet needed)
        ▼
Laptop B (browser only)
  opens http://<A's-IP>:5000 — same catalog, same sales

Day close (on A): summary screen → CSV export → done
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

CREATE TABLE sales (               -- one row per completed sale
  id          INTEGER PRIMARY KEY,
  day         TEXT NOT NULL,       -- 'YYYY-MM-DD' local date
  ts          TEXT NOT NULL,       -- ISO local time
  method      TEXT NOT NULL,       -- 'cash' | 'octopus'
  total_cents INTEGER NOT NULL,
  device      TEXT NOT NULL        -- 'A' | 'B' — which laptop took it
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
- **Stock is derived from reality, not math**: decrement on sale; stock column is the live count. Low-stock = warning at 0, not a hard block (staff can restock mid-day).
- A `day` column on every sale keeps the model multi-day-ready even though the fete is one day (A5).

### 4.3 Catalog CSV contract (proposed — pending the real sample, Q4)

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
4. Both laptops see the new stock/total immediately (single DB, WAL mode).

**Close the day** (at the end)
1. "Close day" → summary: revenue cash / revenue octopus / total; per-item quantities; stock deltas (sold per item).
2. Cash reconciliation sheet: expected cash drawer (opening float + cash sales) vs counted — the team fills in the count, the app shows the difference.
3. Export: `sales-YYYY-MM-DD.csv` (per sale: time, items, method, total) + the summary printed on screen.

**Void / refund** (v1)
- Last-sale undo within a day: flags the sale as voided (kept in the log, excluded from totals), stock restored, difference shown on the day summary.

### 4.5 Concurrency & the LAN edge

- SQLite in WAL mode with short transactions is plenty for a stall (a handful of transactions per minute). A "sale complete" is one transaction.
- If laptop B loses the Wi-Fi mid-day (Q6): **v1 fallback** — B runs a standalone instance against its own local DB, keeps selling, and at close exports its CSV which A merges (same import path, `sales` tagged with device). MVP just notes it in the error state and keeps A's data authoritative.

---

## 5. Roadmap

### Phase 0 — Validate before building (1–2h, this week)
- Answer the open questions in §8 with the team (Q1–Q7).
- Get a **real sample catalog CSV** — the exact file the team would bring (Q4). It defines the import contract.
- Decide receipts (Q2) and confirm the Octopus reader (Q3).

### Phase 1 — MVP (~20–24h)
Scope: CSV import with validation · sell screen (grid, cart, cash/Octopus) · stock decrement + zero warnings · SQLite schema above · single-laptop offline mode · LAN mode (laptop B via browser) · day close (summary, reconciliation sheet, CSV export) · bundled local assets (zero internet).
Acceptance:
- A 50-item catalog imports in one step with per-line errors; re-import updates cleanly.
- A sale (3 items, cash) completes in under 5 seconds from item tap to total.
- Stock matches hand-count after 20 mixed test sales; zero-stock items can't be added to cart.
- Laptop B on the same Wi-Fi sees every sale from A and can sell simultaneously; totals reconcile.
- With Wi-Fi fully off, laptop A sells normally end-to-end.
- Day close totals match a hand count; CSV export opens cleanly in Excel.
- No internet is touched at any point (verify: no CDN requests in devtools).

### Phase 2 — v1 (+6–10h)
Scope: B standalone fallback + CSV merge · void/refund (flagged, not deleted) · receipt print (browser print) · product quick-edit (price/stock) · low-stock alert at a threshold · nicer mobile/touch styling.
Acceptance:
- B sells through a Wi-Fi outage, merges into A at close, day totals still reconcile.
- Void restores stock and excludes the sale from totals; the log still shows it.
- Receipt prints from either laptop in under 10 seconds.

### Phase 3 — v2 (optional, +4–6h)
Scope: printable price list from the catalog · multi-day log view · multi-stall merge (if the fete grows) · barcode scan (any USB scanner types the product code — needs codes in the CSV, Q4 extension).

**Total effort: 26–34h** to a complete, rehearsed system. Cost: $0. Maintenance: none (it's a local app; the repo is the backup).

---

## 6. Risks & Gotchas

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Venue Wi-Fi unreliable/absent** | medium | High | MVP runs on laptop A alone (no network needed). LAN mode uses the stall's own hotspot if needed. B fallback in v1. Q6. |
| **CSV doesn't match the assumed format** | near-certain (first time) | Medium | Phase 0: get the real sample file and lock the contract before writing the importer. Errors report line+column. |
| **Octopus reader availability / settlement** | medium | High | Confirm the reader + who brings it (Q3). App records only; the reader's own batch settlement handles the money. |
| **Floating-point money bugs** | certain if careless | Medium | Prices stored as integer cents; no float arithmetic anywhere. |
| **SQLite corruption (power cut)** | low | Medium | WAL mode; `sales` and `products` are small; export CSV at close is the backup. Daily autosave on the day screen. |
| **Two laptops diverge mid-day** | low | Medium | Single shared DB in MVP; per-sale device tag; v1 merge path tested explicitly. |
| **Scope creep (barcodes, receipts, analytics)** | medium | Low | Everything beyond §5 Phase 1 is explicitly v1/v2 and gated on rehearsal time. |
| **Team doesn't rehearse** | medium | High | Phase 0 ends with a 1-hour dry run: both laptops, sample catalog, 20 fake sales, day close. The fete is not the first run. |
| **Price changes mid-day** | medium | Low | Quick-edit (v1); unit price snapshotted on line items, so history stays true. |

---

## 7. Effort summary

| Phase | Hours | Window |
|---|---|---|
| Phase 0 — validate | 1–2h | this week |
| Phase 1 — MVP | 20–24h | by end of September (dry-run-able) |
| Phase 2 — v1 | 6–10h | October, before rehearsal |
| Phase 3 — v2 (optional) | 4–6h | only if time remains |
| Rehearsal | 1h | the week before the fete |

Deadline 2026-10-31 leaves ~2 weeks of buffer after v1 for real-world fixes.

---

## 8. Open Questions (confirm with the team this week)

1. **What exactly is device 2?** (Another laptop? A tablet? Affects touch-target sizing — Q1.)
2. **Are receipts required?** (If yes: thermal 80mm printer at the stall, or browser-print on whatever printer exists — Q2.)
3. **Octopus: does the stall have a standalone Octopus reader, and who brings it?** (App records method/amount only; the reader settles its own money — Q3.)
4. **Can we get the real catalog CSV?** (Lock the column contract from the actual file, not a guess — Q4.)
5. **Void/refund needed at the fete?** (MVP records only; void is v1 — Q5.)
6. **What's the network situation at the venue?** (No Wi-Fi → single-laptop MVP is the default; some Wi-Fi → LAN mode; our own hotspot → best case — Q6.)
7. **Is the fete one day?** (Model already supports multiple; only the close-day flow assumes one — Q7.)

---

## Appendix — Why no "verified sources" section

Unlike the Scheduler plan (which had to verify Cloudflare/Telegram free tiers), this app is **100% local** — Flask, SQLite, and a browser are already in the team's proven toolkit (the Lateness app runs the same stack). There are no free-tier limits to verify because there is no third-party service in the critical path.

*Confidence: overall 0.85. Remaining variance: Q1 (device form factor), Q3 (Octopus reader), Q6 (venue network) — each moves it ±0.05.*

---

## Update log
- 2026-08-15: Initial plan. Requirements from Elijah: CSV catalog, 2 devices at 1 stall (laptops), fully offline, cash + Octopus, deadline end of October. Plan written as a standalone file per instruction — existing repo files untouched.
