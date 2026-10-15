# SafeGrid — Person 2 Session Log

> **Owner:** Person 2 (Risk Engine & Geospatial Processing)
> **Branch:** `feature/risk-engine`
> **Scope:** Local working log for Person 2's work in `backend/app/risk/`.
> Update this file at the end of each session.
> Note: primarily Person 2's work. Other teammates' work is recorded only where it directly affects Person 2.

---

## Current State (quick reference)

- **Last updated:** 2026-10-15
- **Branch:** `feature/risk-engine` — **2 commits ahead of `origin/feature/risk-engine`** (not pushed): `d029915` (rain cleanup), `55dd2fc` (merge of `origin/feature/data-ingestion`).
- **Subsystem:** `backend/app/risk/` (rainfall engine implemented; geometry toolkit; earthquake spec'd, not coded)
- **Working tree:** clean except untracked: `.opencode/`, `opencode.json`, `test.py`, `test1.py`.
  - Standing permission (2026-10-11): Person 2 grants commit/push of `session_log.md` at will — **this file only**.
- **Blocker 2 CLOSED (Person 1, `dc525cb`):** `/api/risk-zones` implemented (`backend/app/api/risk_zones.py`) + registered in `main.py`; `list_hazards_with_risk()` → GeoJSON `FeatureCollection`; 3 API tests (`tests/test_api/test_risk_zones_api.py`). `is_live` hardcoded `False` (honest default until P4 freshness lands).
- **`docs/RISK_MODEL.md` is now Person 1's v2 framework** (Risk = Hazard × Exposure × Vulnerability, phases P0–P4) with Person 2's earthquake spec retained as **§ 12**.
- **Rain engine cleanup (Person 2, `d029915`, 2026-10-15):** dropped `badge`/`summary`/`factors`/`disclaimer` prose, stale `duration` fallback, duplicate `id` key; standardised `Hazard.probability` docs to 0–100%. `pytest`: **18 passed**.
- **Branch vs `main`:** `origin/main` merged into `feature/risk-engine` earlier (`11ffb82`). Local `main` = `7362ac7` = `origin/main`.
- **Next up:** 🟠 rain.py 11-task list — task 1 (tests, `tests/test_risk/` still a stub) is the highest-value unblocked item; #2 (`window > 1` → 24h) and #8 (unsourced radius heuristic) postponed by P2; #6 (hardcoded id/source fallbacks) awaiting P2 approval; #4 (move CLI to `scripts/`) and #9 (docstring duplication of RISK_MODEL) offered, not yet done; #11 grid migration blocked on the per-user-vs-shared decision. Earthquake: RISK_MODEL § 12 drafted; **pick the GMPE** then build `earthquake.py`.
- **Reminder:** send the short WhatsApp summary to the team (architecture proposal drafted 2026-10-12, pending their input).

### Cross-team status (as of 2026-10-11)

| Person | Branch | In `main`? | Latest work |
|---|---|---|---|
| P1 Rajat (backend/ingestion) | `feature/data-ingestion` | yes (PR #5) | New 3-tier flow + `DataRecord` model (`models/data.py`) |
| P4 Syed (database/offline) | `feature/database` | yes (merged via data-ingestion) | IndexedDB cache + service worker, DB contract tests |
| P3 Suchith (frontend/map) | `feature/frontend-maplibre-ui` | no | `4f4ab42` align MapLibre UI with backend schema |

### Changes in `main` that affect Person 2

- New `backend/app/models/data.py` → `DataRecord` (`data_type`, `source`, `timestamp`, `location`, `magnitude`, `probability`, `specific_data`).
- Person 1 added `identify_hazard(DataRecord) -> Hazard` to `backend/app/risk/classifier.py` — cross-subsystem edit with TODOs assigned to Person 2.
- Flow is now: `DataRecord (raw) → identify_hazard() → Hazard → classify() → RiskResult`.
- `Hazard.probability` redefined as **0–100%**.
- **Gap:** Open-Meteo ingestion emits `data_type="weather"`; `identify_hazard` sets `hazard_type="weather"`, but `classify()` only accepts `"rainfall"` → `NotImplementedError` on the real pipeline.

---

## 2026-10-07 — Repo setup + precipitation engine prototype

### 1. Repository Setup & Team Collaboration

- Cloned the repository from `Safregrid/SafeGrid` and set up the local workspace.
- Reviewed & merged **PR #1** ("Update team member names in README") into `main`.
- Aligned with the assigned ownership branch: `feature/risk-engine` (Person 2: risk engine & geospatial processing).

### 2. Architecture & Domain Analysis

- Studied `Brain-Part-1.md`, `Brain-Part-2.md`, `README.md`, and `RISK_MODEL.md`.
- Defined the Person 2 integration boundary — the contract between Person 1 (Open-Meteo hazard ingestion), Person 2 (risk engine classification), Person 4 (database), and Person 3 (MapLibre visualization).
- Identified the core hazard rule: low risk (🟢) must **never** be described as "absolute safety" — embedded into risk logic.

### 3. Precipitation Risk Engine Prototype (`test.py`)

Built a standalone program modeling precipitation risk calculation prior to backend API readiness:

- **Open-Meteo parameter modeling:** location (latitude, longitude) + ISO timestamp; precipitation (mm) across hourly (1h) and daily (24h) windows; secondary factors `wind_speed_kmh`, `wind_gusts_kmh`, WMO `weather_code`, `precipitation_probability`.
- **Deterministic classification & continuous severity score (0.0–10.0):**
  - 🟢 Low Risk (< 4.0): `< 2.5 mm/h` or `< 15.5 mm/24h`.
  - 🟡 Moderate / Potential Risk (4.0–6.9): `2.5–7.6 mm/h` or `15.6–64.4 mm/24h`.
  - 🔴 High Risk (>= 7.0): `> 7.6 mm/h` or `> 64.5 mm/24h`.
- **Compounding power-grid hazards:** severity escalation for high wind gusts (>= 65 km/h) and convective storm codes (WMO 95/96/99).
- **Execution modes:** interactive mode, demo mode (`--demo`), CLI/JSON export (`--rain`, `--wind`, `--json`); Windows UTF-8 stdout config for clean emoji rendering.

### 4. Git & Codebase State

- Work self-contained in local `test.py`; nothing committed/pushed, branch kept clean.

---

## 2026-10-09 — Finalize `rain.py` + git setup

### 1. Finalized & Refactored `rain.py`

- Purged CLI & demo code (from `test.py`) so `rain.py` serves strictly as the production precipitation risk engine.
- Verified compatibility with the team's agreed `Hazard` schema changes (confirming `duration` was dropped from the data flow).
- Confirmed inputs match the ingestion feed (Open-Meteo / DB) and outputs produce deterministic risk ratings (LOW/MODERATE/HIGH), severity scores (0.0–10.0), and GeoJSON polygons for MapLibre.

### 2. Git Setup & Push

- Configured git author identity (`SpooledUpTurbo`) and addressed the Windows LF→CRLF warning.
- Committed & pushed `887bb98` — **feat(risk): added precipitation risk calculation engine**.
- Clarified git tracking behavior (changes need `git add`, `commit`, and `push`).

### 3. Decided Next Steps

- Reviewing team commits (Afroz, Rajat), the next logical module is the **earthquake risk engine** (following `rain.py` structure).

### 4. Daily Work Log (Person 2)

- Reorganized the backend by moving `rain.py` into `backend/app/risk/` for better module organization.
- Cleaned up `classifier.py` to match the updated structure.
- Encountered and resolved several `pytest` failures in `backend/tests`; reran tests to verify.
- Committed and pushed the updates to GitHub.
- **Next:** implement and refine hazard classification logic, building on the current backend structure.

---

## 2026-10-11 — Session log conversion

- Converted local `log.txt` into this `session_log.md` for proper markdown rendering and easier appends.

---

## 2026-10-11 — Risk-engine review received + threshold docs published

### Review received (Person 2's risk engine)

Full 10-item review of `backend/app/risk/`: 2 blockers, 3 must-fix, 5 cleanup.

- 🔴 **Blocker 1:** `classify()` raises on real Open-Meteo data — `data_type="weather"` → `hazard_type="weather"` but `classify()` only accepts `"rainfall"`. Needs a `data_type → hazard_type` mapping agreed with Person 1.
- 🔴 **Blocker 2:** nothing calls the engine — `identify_hazard()`/`classify()` imported nowhere; `/api/risk-zones` still a stub.
- 🟠 **Must-fix:** zero tests; `RISK_MODEL.md` placeholder (in `HEAD`); duplicated/drifted `compute_rainfall_polygon()` in `rain.py` and `geometry.py`.
- 🟡 **Cleanup:** fabricated affected area; import-time `stdout.reconfigure()`; emoji/summary baked into engine; hardcoded source/hazard_type defaults; `main()` CLI in the package.
- **Reconciliation prerequisite:** local branch is behind `origin/main`; `rain.py` is identical, but `origin/main` adds `models/data.py` + `identify_hazard()`.

### Work completed today

- 🟢 **#4 closed:** `docs/RISK_MODEL.md` rainfall thresholds, compounding factors, and affected-area scaling filled in with value/justification/source/limitations + change log. Committed `164280c` and **pushed to GitHub** (`origin/feature/risk-engine`).
- 🟢 **#7 addressed (local, uncommitted):** removed the import-time `sys.stdout.reconfigure()` side effect from `rain.py`; moved it into `main()` (CLI entry only). `py_compile` passes.
- **Proposed sequencing for remaining items** captured in the review response (merge `origin/main` → mapping → pipeline seam → tests → geometry dedup → cleanup).

### Unresolved / observed

- `classifier.py` has an **unexplained local edit** (`"rainfall"` → `"precipitation"`) not made by us; left unstaged. Must be reviewed before merge.
- Untracked/loose files still present: `.opencode/`, `opencode.json`, `test.py`, `test1.py`.

---

## 2026-10-11 — EOD: IMD hourly switch + provider type mapping (Blocker 1 closed)

### Session-logging infrastructure (earlier today)

- Added `.opencode/session-logging.md` (consolidated log on every sign-off/milestone), `.opencode/scripts/session_digest.py` (read-only export of today's opencode sessions), `opencode.json` (loads the rule), `.opencode/rules.md` (no git-history changes without permission; ask before anything costing money; checkpoint `session_log.md` before token/compaction limits; when unsure, ask).
- Used `opencode.json` + `.opencode/` instead of adding `AGENTS.md`, because `AGENTS.md` already exists on `origin/main` (an add/add conflict on merge); `main` has neither `opencode.json` nor `.opencode/`.
- `session_digest.py --date 2026-10-11` verified: reads 5 sessions today.

### Review received + work completed

- Full 10-item risk-engine review (2 blockers, 3 must-fix, 5 cleanup) analyzed; sequencing proposed (see mid-day entry above for the review detail).
- 🟢 **#4 closed & pushed:** `docs/RISK_MODEL.md` rainfall thresholds + change log → commit `164280c`, pushed to `origin/feature/risk-engine`.
- 🟢 **#7 addressed (uncommitted):** import-time `sys.stdout.reconfigure()` moved out of `rain.py` into `main()`; library no longer touches stdout on import.
- **Local `main` updated:** `git fetch origin main:main` → local `main` = `7362ac7` = `origin/main` (Person 1's `feature/data-ingestion` fully merged into `main`).
- 🟢 **`session_log.md` tracked & pushed:** committed `b6f0935`, pushed to `origin/feature/risk-engine`. Standing permission granted for this file only.
- **`"precipitation"` confusion resolved:** that `classifier.py` edit was Person 2's own action. Checked every remote branch — no `data_type`/`hazard_type` equals `"precipitation"` anywhere (only the `precipitation_mm` parameter). **Canonical label decided: `"rainfall"`**; local edit reverted.
- **Merge with `main`:** Person 2 ran `git merge origin/main` → `11ffb82`, clean, no conflicts. Gained `models/data.py` (`DataRecord`) + `identify_hazard()` placeholder.

### 🔴 Blocker 1 closed (uncommitted): provider type mapping

- Added `RAW_TYPE_TO_HAZARD_TYPE: dict[str, str] = {"weather": "rainfall", "seismic": "earthquake"}` and helper `map_data_type_to_hazard_type(data_type) -> str | None` in `backend/app/risk/classifier.py`.
- `identify_hazard()` now maps the provider's raw `data_type` to our canonical `hazard_type` and returns `None` for unmapped labels (skip, don't raise).
- Verified: `weather→rainfall`, `seismic→earthquake`, `foo→None`; end-to-end `DataRecord(weather) → Hazard("rainfall") → classify()` → `HIGH`, severity 10.0, no `NotImplementedError`.
- Decision recorded: the mapping table is the single anti-corruption layer for provider vocabulary; the `"seismic"→"earthquake"` row is ready for the future earthquake engine.

### IMD attribution + hourly switch to IMD spell-rate

- Verified full form: **IMD = India Meteorological Department** (Ministry of Earth Sciences, Govt. of India).
- 24h bands already matched IMD's official classification (now explicitly attributed in `docs/RISK_MODEL.md`).
- Confirmed our hourly bands were UK Met Office/WMO (not IMD); Person 2 approved switching hourly to **IMD spell rate** (1 cm/h = 10 mm/h).
- `backend/app/risk/rain.py`: hourly bands `<10 / 10–20 / 20–30 / 30–50 / 50–100 / >100` mm/h → 🟢LOW / 🟡MODERATE / 🔴HIGH with severity tiers Light 0–3.9, Moderate 4.0–6.9, Intense 7.0–8.4, Very intense 8.5–9.4, Extremely intense 9.5–9.9, Cloudburst 10.0.
- `WMO_DESCRIPTIONS` replaced with the accurate full WMO-No. 306 / Open-Meteo table (27 codes, incl. previously-missing `97` Heavy thunderstorm); HIGH floor now `82, 95, 96, 97, 99`. Module docstring rewritten (IMD justification).
- `docs/RISK_MODEL.md`: hourly section = IMD spell-rate table (6 rows) + severity mapping; change-log row added.
- Verified boundaries: `9.9→LOW`, `10→MODERATE`, `20→HIGH(7.0)`, `30→HIGH(8.5)`, `50→HIGH(9.5)`, `100+→HIGH(10.0)`; 24h path unchanged; WMO `97` forces HIGH. `pytest`: **15 passed**, no regressions.

### Git state (EOD)

- Committed & pushed: `164280c` (docs RISK_MODEL), `b6f0935` (session_log).
- 🟢 **Pushed (EOD):** `9586f36` (classifier.py type mapping), `874fdd8` (rain.py IMD spell-rate hourly + WMO codes), `cfcdcff` (RISK_MODEL.md IMD hourly + mapping change-log row).
- Committed, **not pushed**: `11ffb82` merge of `origin/main` into `feature/risk-engine` (branch ahead of `origin/feature/risk-engine` by 25).
- Uncommitted (pending Person 2 approval before commit): none.
- Untracked: `.opencode/` (`rules.md`, `session-logging.md`, `scripts/session_digest.py`), `opencode.json`, `test.py`, `test1.py`.
- `main` = `7362ac7` = `origin/main` (up to date).

### Next up

- Commit/push pending engine + doc changes (confirm message) and the `11ffb82` merge.
- 🔴 **Blocker 2:** wire the engine in — `app/risk/pipeline.py` seam (`evaluate` / `evaluate_and_store`), `/api/risk-zones` consuming persisted `RiskResult`s, documented in `docs/API.md` + `ARCHITECTURE.md`.
- 🟠 Tests (`test_classifier.py` / `test_geometry.py` / `test_rain.py`); geometry dedup (`geometry.py` as home, carrying the ±89.9-lat clamp + lon normalization fixes from `rain.py`).
- 🟡 Cleanup 6–10: affected-area honesty framing; emoji/summary out of engine output; hardcoded source/`hazard_type` defaults; `main()` → `scripts/`.
- Earthquake engine (the `seismic→earthquake` mapping row is already in place).

---

## 2026-10-12 — Earthquake engine requirements + local-grid vs concentric architecture

### Earthquake engine (`earthquake.py`) — requirements agreed (no code yet)

- **Input contract** (`EarthquakeInput`, mirroring `PrecipitationInput`): `latitude`, `longitude`, `time`, `magnitude`, `mag_type`, `depth_km` *(required)*; `mmi`, `cdi`, `alert`, `tsunami`, `felt`, `sig`, `place` *(optional compounding factors)*.
- **Magnitude decision (confirmed with Person 1):** standardize on the USGS *preferred* magnitude `properties.mag`, **no scale conversion** anywhere. Magnitude scales (`ml`/`mb`/`ms`/`mww`/…) are not mutually convertible, so conversion would fabricate precision. `magType` passes through as metadata; `RISK_MODEL.md` will note we do **not** cross-convert to IMD's local magnitude (`ML`).
- **India scope:** USGS is global → filter to an India bounding box (lat 6–38, lon 68–98, incl. Andaman & Nicobar). Candidate threshold sources to cite: BIS IS 1893 (Part 1) seismic zones II–V, IMD/NDMA, USGS PAGER/MMI.
- **Thresholds NOT yet fixed** — must be written into `docs/RISK_MODEL.md` (value/justification/source/limitations) *before* implementing classification logic (project rule).
- **Integration:** add `_classify_earthquake` + branch in `classifier.py`; `RAW_TYPE_TO_HAZARD_TYPE` already maps `seismic→earthquake`; USGS ingestion (`backend/app/ingestion/usgs.py`) is Person 1's stub.

### Map-geometry architecture — debated, proposals pending team confirmation

- **Two data models, not one:** rain (Open-Meteo) can be sampled at any coordinate → grid is genuinely data-driven; earthquakes (USGS) are *events* at epicenters → event-based, not grid-sampleable. Proposal: **rain = sampled grid, earthquake = concentric attenuation rings**, drawn on the same display grid for visual consistency.
- **Verified Open-Meteo constraints:** max **1000 locations/request** (`LOCATIONS_LIMIT`); **each coordinate counts as an API call** (free tier 10,000/day); POST needed for large batches.
- **New product constraint:** only risky areas *around the user* are shown → the grid is **local**, not national.
- **`n` reasoning:** two knobs — coverage radius `R` and sampling spacing `s` (`n = 2R/s`). Town scale `R≈25 km, s≈2 km → n≈25` (625 cells, fits one request). Spacing must not be finer than the source model (~11 km global). Recommended pilot: town scale.
- **Scale trap:** per-user dynamic grids multiply quota by user count → prefer a **fixed shared grid, computed on a schedule, cached, sliced by radius per user** (aligns with Person 4's service worker).
- **Color representation:** **dissolve/union of qualifying cells by class** (honest; holes preserved) as default; convex hull only per connected component and must be labelled an envelope (spans non-risk gaps otherwise).
- **Open question:** for a purely local view, rain may not need a grid at all — one point request + affected-area ring may suffice.

### Geometry ownership (hybrid — matches earlier plan)

- `geometry.py` = **shared toolkit of primitives** (point→circle/ring, concentric rings, grid builder, cell polygon, dissolve/union, convex hull, simplify) — no hazard knowledge.
- `rain.py` / `earthquake.py` = **thin recipes** composing primitives + hazard-specific decisions (radius scaling; attenuation radii).
- **Dedup:** remove the duplicated `compute_rainfall_polygon` from `rain.py`; keep one copy in `geometry.py`, carrying the ±89.9-lat clamp + lon-normalization fixes from `rain.py`. Closes the drift item from the 2026-10-11 review.

### DB / offline contract (with Person 4) — Q&A

- **`affected_area` stays one GeoJSON geometry per `RiskResult`; `MultiPolygon` is acceptable. No per-cell storage** on the hazard / risk-result tables. The grid is an internal computation detail; what is persisted/rendered is the *dissolved* polygon.
- **Event hazards vs grid layer are different objects:** event hazards (earthquake epicenter, point-rain) stay keyed by `hazard_id` with one geometry each; the shared rain grid is **not** a hazard. If persisted it needs a separate cache table (e.g. `grid_cells(cell_id, lat, lon, score, risk_level, computed_at)`), else it is left to the service-worker cache. **Optional — flagged to Person 4.**
- **Refresh cadence / TTL is Person 4's to set but is source-dependent (pending Person 1):** rain grid is quota-bound (n=25 → 625 calls/refresh; ~3-hourly ≈ 5,000 calls/day fits the 10k free tier); the USGS quake feed is ~real-time with no key/quota → 1–5 min. Suggested `is_live = (now − generated_at) <= interval`; expose `is_live` **and** `generated_at`; offline → `is_live = False`.
- Replied to Person 4 on (1); (2) declared dependent on Person 1. Future suggestion: drop `n` to 15 for fresher refreshes within quota (no schema impact).

### Secondary / cascading hazard layer (proposal, no code)

- Idea (Person 2): after classifying a primary hazard, use geography to flag *secondary* hazards — heavy rain in hilly terrain → landslide; in low-lying areas → flooding; extend later to earthquake → tsunami.
- **Recommendation:** do **not** embed in `rain.py`. Create a shared, hazard-agnostic `app/risk/secondary.py` (`(primary_hazard, geography) → list[SecondaryRisk]`), invoked by the pipeline *after* primary classification, keeping primary engines thin/pure.
- **Vocabulary:** keep "compounding factor" (raises primary severity — e.g. wind/WMO in `rain.py`) distinct from "secondary hazard" (a different hazard type *triggered* by the primary).
- **Blocker is geography data, not logic:** cheapest = Open-Meteo **Elevation API** (`/v1/elevation`, Copernicus DEM 90 m, no key, ≤100 coords) → derive slope; heavier = static India layers (GSI landslide susceptibility, Bhuvan/ISRO, IMD/NDMA flood zones). Document whichever is used as a known limitation.
- **Two decisions before code (need P3/P4):** (a) output shape — secondary risk attached to the primary `RiskResult` vs its own `RiskResult` / zone with geometry; (b) new thresholds must be documented in `RISK_MODEL.md` *first*.
- **Tsunami extension:** simplest version uses the existing USGS `tsunami` flag + offshore/shallow + coastal proximity → "conditions consistent with increased risk," never prediction.
- Suggested pilot: rainfall → urban-flood vs landslide only, one geography source, fully documented; then extend.

### Decisions status

- ✅ Confirmed: earthquake input contract; USGS preferred-magnitude / no-conversion rule (Person 1 notified); geometry hybrid direction; `affected_area` = one geometry per hazard, no per-cell storage (Person 4).
- ⏳ Pending team: coverage radius `R`; grid `n`/spacing; shared-vs-per-user grid; union-vs-hull; whether rain needs a grid for a local-only view; secondary-hazard layer (`secondary.py`) + its output schema/geography source.
- **Nothing implemented yet** — requirements / architecture / docs only; no code changed today.

### Git state (EOD)

- No code commits today. Commits timestamped 2026-10-12 00:0x (`9586f36`, `874fdd8`, `cfcdcff`, `91a4a3e`, `3c2016b`) are the tail of the 2026-10-11 EOD batch.
- Working tree: `backend/app/risk/session_log.md` modified (uncommitted) — today's entry. Untracked: `.opencode/`, `opencode.json`, `test.py`, `test1.py`.

---

## 2026-10-13 — Blocker 2 pipeline seam (`pipeline.py`)

### What Blocker 2 actually was

- Three layers worked in isolation but were never connected: ingestion writes `data_records`; the risk engine classifies a `Hazard`→`RiskResult`; the DB has `hazards`+`risk_results` and `/api/hazards`. **Nothing turned `data_records` into hazards, ran the engine, or wrote results** → the engine never ran and `/api/risk-zones` was always empty. The missing piece is a connective segment (the "middle pipe"), not broken logic.

### Built: `backend/app/risk/pipeline.py` (committed `dff1a0e`, pushed)

- Person 2's seam composing the classifier + Person 4 repository, no hazard logic of its own.
- `evaluate(record) -> RiskResult | None`: `identify_hazard()` → (skip if `None`) → `classify()`; no persistence.
- `evaluate_and_store(record, database=db) -> RiskResult | None`: same, then `save_hazard()` + `save_risk_result()`. **Classify runs before any writes**, so a classification failure leaves the DB untouched.
- Batch helpers `evaluate_all()` / `evaluate_and_store_all()` skipping unmapped records.
- **Decision:** a record whose `data_type` is mapped in `RAW_TYPE_TO_HAZARD_TYPE` but has no classifier yet (e.g. `seismic→earthquake` before `earthquake.py`) **raises `NotImplementedError` (fail loud)** rather than silently skipping — consistent with deciding not to hide a declared-but-unimplemented hazard type. Unmapped labels still return `None`. Revisit when `earthquake.py` lands.
- Verified end-to-end on an in-memory DB: `DataRecord(weather, 18 mm/h, gusts 50)` → `evaluate` HIGH/7.12 with a `Polygon`; `evaluate_and_store` persisted and `list_hazards_with_risk()` returned the joined row; unmapped `data_type` → `None`. `pytest`: **15 passed**, no regressions.

### Scope decision (was asked + answered)

- Person 2 chose **pipeline seam only**. The `/api/risk-zones` endpoint (Person 1's `backend/app/api/risk_zones.py` + registration in `main.py`) is deliberately **left as a cross-subsystem handoff** — not edited today.

### Person 1 decisions received (evening) — all three locked in

- 🟢 **Grid approved (rain, one shared pilot region).** ONE shared grid over ONE pilot region (town scale, `n≈25` → 625 cells), **pre-computed on a schedule and cached**, API **slices per user at request time** (zero runtime provider calls). 3–6h refresh ≈ 2,500–5,000 calls/day, under the 10k free tier. TTL + `is_live` to be set with Person 4. Hard rules: **never per-user dynamic, never national.**
- 🟢 **Rings kept (earthquake).** Rings were always acceptable; they're wrong for rain (circle invented from a score) but right for earthquakes (radial decay is real physics; a quake is an *event*, not a field). Requirement: **ground rings in a published attenuation relation** — radius from `mag + depth + distance → intensity` — and **draw at MMI thresholds, not invented steps**. "Depth does the work." **Non-Mw `magType` → note it, do not convert.**
- 🟢 **Tsunami secondary hazard, strict trigger.** Require **all four**: USGS `tsunami` flag = 1 **and** shallow (`< 70 km`) **and** offshore **and** `M ≥ 6.5` (documented as a working assumption). Coastal band becomes a **separate secondary `RiskResult`** (own geometry, own score) via `secondary.py` — **never folded into the shaking score**. Needs a coastline dataset (**Natural Earth**). Label: *"conditions consistent with increased risk — not a prediction."*
- **Gating rule re-stated by Person 1:** both new threshold sets go into **`docs/RISK_MODEL.md` before code**. Earthquake engine declared **unblocked**.

### Earthquake spec written to `docs/RISK_MODEL.md` (docs only)

- Replaced the `Earthquake (USGS) — PLACEHOLDER` section with a full **specification draft** (change-log row added). Canonical detail lives in RISK_MODEL.md — this log only points to it.
- Contents: USGS input contract (`properties.mag`/`magType`, `depth_km`, coords, `time`; optional `mmi`/`cdi`/`alert`/`tsunami`/`felt`/`sig`); India bbox scope (lat 6–38, lon 68–98); **locked no-conversion magnitude decision — "Richter"/ML explicitly rejected** (ML saturates ~M6.5–7, not the GMPE input, not reliably provided by USGS for significant events); MMI-based threshold framework (proposed bands LOW <IV, MODERATE IV–V, HIGH ≥VI); concentric intensity rings via hypocentral distance `sqrt(d_epi²+depth²)`; non-mw `magType` → classify + low-confidence note.
- 🔴 **Open input: which GMPE** (candidate USGS ShakeMap Worden et al. 2012 MMI, or an India-region relation) — coefficients/source/limitations must be cited before any code. Fixed the stale "Richter magnitude" placeholder text.
- Also captured (not yet in RISK_MODEL): the **adaptive-refresh** discussion for the rain grid — rolling 24h window + UTC-hour-aligned polling are good; tightening the **whole** 625-cell grid during HIGH is a quota trap (7.5k/day already at a 2h cadence) → refresh a **small affected subset** fast, keep the full grid slow, add hysteresis + a daily budget guard; the 15-min full-grid cadence is dropped. P4 must store `generated_at` per zone for a dynamic `is_live`.

### rain.py / geometry.py cleanup (afternoon, committed `8dcca71`, pushed)

- 🟢 **Geometry dedup (review must-fix closed):** `point_circle()` primitive + `compute_rainfall_polygon()` (score→radius) + `concentric_rings()` now live **only** in `geometry.py`. `rain.py` imports `compute_rainfall_polygon` from there (verified same function object). Carried the ±89.9-lat clamp + lon-normalization into the single copy. Deleted the **dead** `compute_affected_area()` (zero callers) from `geometry.py`.
- 🟢 **Concentric rings prepared for `earthquake.py`:** `concentric_rings(lat, lon, radii_km, num_points=24) -> list[Polygon]` (nested circles; annulus bands = difference of consecutive rings, documented). Not wired to anything yet.
- 🟢 **Probability edge fixed** (`rain.py`): removed the `0.0 < p <= 1.0 → ×100` guess; all values are treated as **percent** and clamped to `[0,100]`. A genuine `1.0` now reads as 1%, not 100%.
- 🟢 **String parsing removed from the engine** (`rain.py`): `process_precipitation_hazard()` now accepts only a dict / Pydantic model; the JSON parse moved into `main()` (CLI concern). Dropped unused `import ast` / `import math`.
- ⚠️ **New: CLI must run as a module.** `rain.py` now imports `app.risk.geometry`, so `python app/risk/rain.py` fails (`No module named 'app'`). Use `python -m app.risk.rain` from `backend/`. Revisit when `main()` moves to `scripts/`.
- Verified: circle closes + clamps; 3 concentric rings; prob `1.0`→"1%"; Hazard-model input still classifies; CLI via `-m` prints. `pytest`: **15 passed**.
- **Design agreed this afternoon (not built):** rain moves fully to a **grid** — grid drawn around the user's location, town-sized; cells store only HIGH/MODERATE (no green); per-class remark = *"up to X mm/hr in red areas"* (X = grid max) and similar for moderate; render one **MultiPolygon per class** (disjoint components = honest). ⚠️ **Conflict to resolve:** "grid around the user's location" implies a **per-user dynamic grid**, which Person 1 explicitly forbade (quota) in favour of ONE shared pilot grid. Flag before building.

### Remaining tasks w.r.t `rain.py` (11 — carry forward)

1. **Unit tests** — `tests/test_risk/` is still a stub. Highest value; fully unblocked (engine needs no network/DB/pipeline).
2. **`window > 1` treated as 24h** — `calculate_precipitation_risk` maps any window `> 1 h` onto the 24h bands. Needs a decision (round, reject, or per-window tables).
3. **Stale `duration` fallback** — `process_precipitation_hazard` still reads `data.get("duration")`, contradicting the "duration dropped" decision. Remove or justify.
4. **`main()` CLI embedded in the package** — move to `scripts/` (also removes the `python -m app.risk.rain` requirement introduced today).
5. **Presentation baked into the engine** — `badge` (emoji), `summary`, `disclaimer`, and the `factors` prose belong in the API/frontend layer, not the engine.
6. **Hardcoded identity fallbacks** — fabricated `"open-meteo:unknown"` id, `"open_meteo"` source, hardcoded `hazard_type="rainfall"`. Don't invent identity fields.
7. **Redundant output keys** — both `id` and `hazard_id` returned.
8. **Unsourced radius heuristic** — `compute_rainfall_polygon` radius scaling is a heuristic (now labelled in `geometry.py`); ideally grounded in a cited source or explicitly accepted as a limitation.
9. **Docstring/`RISK_MODEL.md` duplication** — the module docstring re-states every threshold table → drift risk; trim to a pointer at `docs/RISK_MODEL.md`.
10. **`models/hazard.py` doc inconsistency** — `probability` is documented as both `0.0–1.0` and `0 to 100%`; standardise on 0–100 (matches the engine's new percent handling).
11. **Grid migration (big, blocked)** — grid builder + per-cell scoring + one `MultiPolygon` per class + a new story for a rain hazard's `affected_area` (currently `NOT NULL`). Blocked on the per-user-vs-shared-grid decision and team's `R`/`s`/region.

### Git state (EOD)

- **Pushed today:** `dff1a0e` (`pipeline.py` seam), `8dcca71` (geometry dedup + rain cleanup + earthquake spec), `81b46d5` (quick-ref sync). `feature/risk-engine` in sync with `origin/feature/risk-engine`.
- `pipeline.py`: committed & pushed in the pipeline-seam session (`dff1a0e`); **no changes since — up to date**.
- Working tree: clean. Untracked: `.opencode/`, `opencode.json`, `test.py`, `test1.py`.

### Next up

- Hand `/api/risk-zones` wiring to Person 1 (or get owner's go-ahead): read `list_hazards_with_risk()` → wrap `affected_area` polygons into a GeoJSON `FeatureCollection` per `docs/API.md`; register router in `main.py`.
- Remaining Person 2 review items: tests (`test_pipeline.py`/`test_geometry.py`/`test_rain.py`) and the cleanup backlog — see the **11-task list** above. Geometry dedup ✅ closed (2026-10-13).
- 🟢 **Unblocked by Person 1 (2026-10-13):** earthquake engine. Sequence: (1) `docs/RISK_MODEL.md` sections for attenuation/MMI + tsunami trigger; (2) `earthquake.py` + `_classify_earthquake`; (3) `geometry.py` concentric-ring primitive; (4) tsunami `secondary.py` (needs Natural Earth coastline + a P4 schema decision for storing a second `RiskResult`).

---

## 2026-10-15 — Merge Person 1's `data-ingestion` + rain-engine cleanup (tasks 3/5/7/10)

### Rain engine cleanup (committed `d029915`)

- Worked through the 11-task list with P2. **Done:** #3 (removed the stale `duration` fallback from window extraction and the CLI demo payload — `duration` is dropped project-wide), #5 (removed `badge`/`summary`/`factors`/`disclaimer` presentation prose from `PrecipitationRiskResult` and the output dict; scoring logic — wind/WMO floors — untouched), #7 (dropped the duplicate `id` key; `hazard_id` is canonical for `classifier.py`, `RiskResult`, and the DB), #10 (`Hazard.probability` docs standardised to 0–100% in `models/hazard.py`).
- **Postponed by P2:** #2 (`window > 1` treated as 24h) and #8 (unsourced `compute_rainfall_polygon` radius heuristic).
- **Awaiting P2 decision:** #6 (hardcoded `"open-meteo:unknown"` id / `"open_meteo"` source / `0.0,0.0` coord fallbacks — P2 recommended *fail loud*: raise instead of invent identity/coordinates; `hazard_type="rainfall"` stays since this *is* the rainfall engine), #4 (move `main()` CLI to `backend/scripts/`), #9 (trim module docstring threshold tables that duplicate `docs/RISK_MODEL.md`).
- ⚠️ `WMO_DESCRIPTIONS` is now unused reference data, and `PrecipitationInput.precipitation_probability` no longer feeds scoring (it only fed a `factors` note) — both left in place pending P2's call.
- ⚠️ The LOW≠safe disclaimer has no home in the engine now; it must be rendered by the API/frontend (Person 3) — noted for later.
- `pytest`: 15 passed at this commit.

### Merge of `origin/feature/data-ingestion` (merge commit `55dd2fc`)

- Person 1 (Rajat) landed the **pipeline + API wiring**. `merge-base` was `dff1a0e` (our pipeline-seam commit). Incoming since then:
  - `dc525cb` — **`/api/risk-zones` implemented** (`backend/app/api/risk_zones.py`): `list_hazards_with_risk()` → GeoJSON `FeatureCollection`, filters to drawable `Polygon`/`MultiPolygon`, `is_live: False` honest default; registered in `main.py`; new `backend/tests/test_api/test_risk_zones_api.py` (+82).
  - `docs/RISK_MODEL.md` rewritten as **v2** (`+339`): Risk = Hazard × Exposure × Vulnerability, phases P0–P4, confidence model, exposure/vulnerability feeds, calibration store.
  - New `docs/WORKLOG.md` + `CONTRIBUTING.md` addendum; frontend MapLibre/UI updates (P3).
  - Person 1 did **not** touch `backend/app/risk/` — no clash with our engine code.
- **One conflict: `docs/RISK_MODEL.md`.** Person 1 had also merged our branch (`264fb53`) and adopted our IMD rainfall thresholds. Resolution: kept Person 1's v2 framework as the backbone and re-applied Person 2's earthquake specification as a new numbered section **§ 12** (our only other deltas were the status line and one change-log row). Fixed § 4's earthquake pointer and § 10 open-decision row 4 to reference § 12; appended change-log rows (earthquake spec 2026-10-13 + this merge).
- **Blocker 2 effectively closed:** the endpoint now consumes persisted `RiskResult`s. Cross-subsystem handoff done by Person 1 (as intended).
- `pytest` after merge: **18 passed** (15 + 3 new risk-zones API tests).

### Git state

- **Committed, NOT pushed** (branch is 2 ahead of `origin/feature/risk-engine`): `d029915` (rain cleanup), `55dd2fc` (merge).
- Untracked: `.opencode/`, `opencode.json`, `test.py`, `test1.py`.
- `main` = `7362ac7` = `origin/main` (unchanged).

### Next up

- Finish the rain.py backlog: #1 tests (`tests/test_risk/` still a stub) first; then #4/#6/#9 (pending P2) and #11 (grid, blocked).
- Earthquake: `RISK_MODEL.md` § 12 stays preliminary — **select the GMPE**, then `earthquake.py` + `_classify_earthquake`; concentric rings primitive already exists in `geometry.py`.

