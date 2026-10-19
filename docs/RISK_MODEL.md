# SafeGrid — Risk Model v2

> **Status: DRAFT SPEC (replaces the v1 placeholder)**
> Author: Person 1 (with Person 2 as owner of `backend/app/risk/`).
> Implementation status: **Rainfall implemented (Person 2, 2026-10-08); Earthquake specification drafted (Person 2, 2026-10-13) — GMPE still unselected, no earthquake code yet.**
> Purpose: define a *defensible* risk framework — **Risk = f(Hazard, Exposure, Vulnerability)**
> — that is data-derived, uncertainty-aware, verifiable, and implementable in stages.
>
> **Reading guide for implementers:**
> - Person 2 (engine): §§ 2–7 define the scoring contract. Implement per phase.
> - Person 4 (DB): § 8 defines the calibration/prediction store. `risk_results` stays primary.
> - Person 1 (API): § 6 defines the per-zone output shape (keeps `/api/risk-zones` GeoJSON contract).
> - Everyone: § 9 is the working-assumption policy — no invented thresholds without a label.

---

## 1. Non-goals (read first)

This project is **not** a certified warning system and cannot claim "accurate" risk assessment
in the public-safety sense — national agencies can't either, and they say so. We target:

> **Defensible risk estimation**: methodologically sound, derived from real data,
> uncertainty shown, thresholds traceable to sources, and *verified against outcomes*.

Reminder of project rules this doc enforces (Brain §5, README, AGENTS.md):

1. Never claim disaster *prediction* or official authority.
2. `LOW` never means safe; limits are always surfaced.
3. Thresholds are documented here **before** implementation, with source + limitation.
4. Unreferenced choices are labelled **WORKING ASSUMPTION** and scheduled for calibration.

---

## 2. Risk framework

```
Risk(polygon) = Hazard(polygon) × Exposure(polygon) × Vulnerability(polygon)
```

Each component is normalized to **0.0–10.0** so the product stays in a familiar scale.
Risk level bands (unchanged from v1, see § 5):

| Risk level | Condition (severity_score) | Meaning |
|---|---|---|
| `HIGH` | ≥ 7.0 | Elevated risk to people/places in the zone |
| `MODERATE` | 4.0 – 6.9 | Potential risk; monitor and prepare |
| `LOW` | < 4.0 | Below elevated-risk thresholds — **not safe** |

The **severity_score ('risk score') is now the *product*** of three sub-scores,
deliberately simpler than a weighted sum so it stays explainable:

```
hazard_index  = intensity/scenario score          (§ 3–4)
exposure_index = people/asset presence in zone     (§ 7)
vulnerability_index = place-level fragility        (§ 7)
severity_score = clamp( hazard_index × (0.1 + exposure_index) × (0.1 + vulnerability_index), 0, 10 )
```

The `0.1 +` terms keep the score from collapsing to zero when one raster is missing
(graceful degradation on partial data). Every sub-score is returned alongside the total
so the UI can show *why* (§ 6).

---

## 3. Hazard — rainfall (Open-Meteo)

Inputs (per grid cell, from Open-Meteo `hourly`): `precipitation`, `precipitation_probability`,
`wind_speed_10m`, `wind_gusts_10m`, `weather_code`. Assessment window:
`time_window_hours` = `1` (hourly rate, § 3.1) or `24` (accumulation, § 3.2).

### 3.1 Intensity thresholds (hourly rate)

Hourly bands follow the **India Meteorological Department (IMD)** rainfall *spell-rate*
classification (cm/h converted to mm/h; 1 cm = 10 mm). This matches the implemented
engine in `backend/app/risk/rain.py`.

| Risk level | Condition (mm/h) | severity_score | Justification | Source | Limitations |
|---|---|---|---|---|---|
| LOW | < 10 | 0.0 – 3.9 | IMD **Light spell** (< 1 cm/h); standard municipal drainage absorbs the runoff | IMD | Clogged drains / poor local topography may still pool |
| MODERATE | 10 – 20 | 4.0 – 6.9 | IMD **Moderate spell** (1–2 cm/h); runoff accumulates on roadways | IMD | Antecedent ground saturation not modelled without soil moisture |
| HIGH | 20 – 30 | 7.0 – 8.4 | IMD **Intense spell** (2–3 cm/h); localised surface-water accumulation and flooding | IMD | Duration matters; brief bursts differ from sustained downpours |
| HIGH | 30 – 50 | 8.5 – 9.4 | IMD **Very intense spell** (3–5 cm/h); waterlogging and grid disruption | IMD | Runoff velocity depends on slope and impermeability |
| HIGH | 50 – 100 | 9.5 – 10.0 | IMD **Extremely intense spell** (5–10 cm/h); severe flash-flood risk | IMD | Gauge/radar needed to separate intense bursts from sustained rates |
| HIGH | > 100 | 10.0 | IMD **Cloudburst** (> 10 cm/h) | IMD | Cloudbursts are highly localised; the forecast grid may miss the peak |

### 3.2 Accumulation thresholds (24-hour total)

24-hour bands follow the **IMD** official rainfall classification (Light 2.5–15.5,
Moderate 15.6–64.4, Heavy 64.5–115.5, Very Heavy 115.6–204.4, Extremely Heavy ≥ 204.5 mm),
mapped onto SafeGrid's three levels:

| Risk level | Condition (mm/24h) | severity_score | Justification | Source |
|---|---|---|---|---|
| LOW | < 15.5 | 0.0 – 3.9 | IMD **Light**; insignificant catchment saturation | IMD |
| MODERATE | 15.5 – 64.4 | 4.0 – 6.9 | IMD **Moderate**; prolonged soaking, rising water tables, localised pooling | IMD |
| HIGH | 64.5 – 115.5 | 7.0 – 8.4 | IMD **Heavy**; regional waterlogging, drainage overwhelm | IMD |
| HIGH | > 115.5 | 8.5 – 10.0 | IMD **Very Heavy / Extremely Heavy**; severe inundation potential | IMD |

### 3.3 Compounding modifiers (applied to `hazard_index`, not the final score)

| Condition | Modifier | Justification | Source |
|---|---|---|---|
| gusts ≥ 65 km/h or speed ≥ 50 km/h | +1.5 | Downed lines, structural stress, wind-driven rain | WMO Beaufort/storm guidance |
| gusts ≥ 45 km/h or speed ≥ 35 km/h | +0.8 | Moderate wind coupling | WMO |
| WMO 95 / 96 / 99 (thunderstorm, ±hail) | floor ≥ 7.0 | Convective storms → rapid onset | WMO weather codes |
| WMO 82 (violent showers) | floor ≥ 7.0 | Extreme convective rates | WMO weather codes |

Forecast `precipitation_probability` < 40% while rain is forecast flags high uncertainty —
surfaced as a confidence downgrade (§ 6.1), **not** a change to the score itself.

### 3.4 Phase-3 upgrade — return period (statistical anchor)

Replace "linear ramp with qualitative labels" with comparison against regional
**return-period rainfall** (e.g. "above the 10-year event"):

- Source: **NOAA Atlas 14** (US) / **IMD IDF curves** (India) per station.
- For the pilot region, precompute threshold tables in `backend/app/risk/data/`.
- Continue emitting a score, but the *evidence string* becomes
  `"90 mm/6h exceeds the regional 10-year return level"` — a citable statement.

> **WORKING ASSUMPTION** until region-specific IDF tables are loaded:
> the v1 linear ramps in § 3.1–3.2 are proxies for return-period exceedance.
> They must be replaced per phase 3 before any public-facing messaging claims magnitude.

---

## 4. Hazard — rainfall geometry is the grid (circles forbidden)

**The affected area is derived from the grid, never from a severity score.** A
fabrication like `radius = f(score)` (the v1 3/5/10 km steps) is forbidden for
rainfall. There is **no circle fallback** — if a cell cannot be scored it is
*no data*, not an invented approximation.

- **Per hazard:** the affected area is the **grid cell** (a square) containing the
  hazard location — one cell, one polygon (`backend/app/risk/grid.py`). Under the
  current pipeline this is what `rain.py` writes to `RiskResult.affected_area`,
  and `/api/risk-zones` renders the square (it accepts `Polygon`/`MultiPolygon`).
- **Standing layer:** a whole region is scored cell-by-cell into a snapshot
  (§ 4.1) — the primary rainfall product that answers "what is the risk here?".
- **Cell size** is a config parameter (`GridSpec.cell_size_deg`), not a constant;
  the default is **0.1° (~11 km)** — the Open-Meteo model resolution, so no
  precision is fabricated. Final value pending § 10 decision 7.

> **WORKING ASSUMPTION**: cell size and the peak-hour window are calibrated per
> region during § 8. They are not physical boundaries.

**Earthquake (USGS)** stays an **event / attenuation model** — circles are correct
there because intensity decays with distance from a source, and the radii come
from a cited MMI relation (not a score). Full specification — input contract,
magnitude decision, MMI thresholds, rings — is in **§ 12**.

### 4.1 Regional risk grid (precomputed snapshot → point lookup)

§ 4 above is the **event-local** footprint: a small grid *around one reported hazard*,
used to derive that hazard's `affected_area`. This subsection is a different object — a
**standing regional grid** that scores a whole area of interest in advance, so a user's
location can be answered instantly from a snapshot.

- **The grid is config, not a place.** A grid is just a **cell size + a region bound
  box**; a named region (a state, a district, the whole country) is one bbox supplied as
  data. Nothing in the code names or hardcodes a region. Cells are indexed against a
  **fixed global anchor** (`-90`, `-180`), so a cell's `cell_id` is stable when the region
  grows — adding a state later does not invalidate the cells already scored.
- **A cell is not a hazard event.** Event hazards keep the existing
  `hazard_id` → `affected_area` contract (§ 6). Grid cells live in their **own storage**
  (e.g. `grid_cells(cell_id, lat, lon, cell_size, risk_level, severity_score,
  precipitation_mm, computed_at)`), because `risk_results.affected_area` is `NOT NULL` and
  keyed by `hazard_id`. *(Storage/retrieval: Person 4.)*
- **Scoring a cell:** a cell is classified at its **peak forecast hour within a window**
  (default **24 h from now**), using the § 3 hourly bands (`time_window_hours = 1`).
  A whole-region run scores every cell and produces **one immutable snapshot**.
- **Run whenever called.** Scoring is a **pure function**
  (`score_grid(spec, forecasts) -> snapshot`); planning a run
  (`cell_requests(spec, region)`) and fetching the weather for those coordinates are
  separate. There is no timer, cadence, or quota logic here — **Person 1 decides how often
  to fetch and calls the run**.
- **Serving a user is a lookup into a snapshot**, not new computation: map the point to
  its cell (`grid.py`) and read that cell's result. *(Added by Person 1, 2026-10-19: when
  no cell is stored, the API may score that one square on demand and store it before
  answering, so a place the runner never visited is still answerable later. The score
  itself is unchanged — same `score_grid()`, sampled at the cell centre — so an
  on-demand cell and a run-time cell are identical.)*
- **Output shape.** Per cell the model stores `risk_level`, `severity_score`, the cell
  polygon, and `computed_at`. The **user-facing answer returns all four** —
  `risk_level` + `severity_score` + cell polygon + `computed_at` — and leaves it to the
  caller/UI to decide whether to display the score.
- **How the region is chosen.** The region is config, not a place, and a user supplies no
  bounding box. A granted location is turned into one two ways: an explicit box, or a
  **declared radius** around the point (`region_around(lat, lon, radius_km)`, Person 1).
  The radius is a **coverage** parameter, not a risk threshold — it decides what we look
  at, never how dangerous something is — and the centre wins over the box when both are
  set. Two honesty points: the radius yields the **bounding box of square cells, never a
  circle**, so the § 4 "circles forbidden" rule is respected (its corners lie up to
  √2 × radius from the centre); and **village boundaries are deliberately not used**,
  because reliable outlines are unavailable to us (OSM coverage is patchy across rural
  Karnataka) and a wrong outline would silently score the wrong ground while looking
  authoritative.
- **Out-of-grid is not LOW.** A point **outside the region** returns an explicit
  *outside-coverage* result; a point inside the region but in an **unscored cell** returns
  *no-data*. Neither is ever reported as `LOW` (see the non-negotiable in § 1).

> **WORKING ASSUMPTION**: the default **cell size is 0.1° (~11 km)** — the Open-Meteo model
> resolution, so no precision is fabricated — and the peak-hour **window is 24 h**. Both are
> parameters, not constants; final values are pending (**§ 10, decision 7**).
> The **coverage radius** defaults to **20 km** (`grid_radius_km`), likewise a declared
> parameter rather than a tuned value.
>
> **DEFERRED (not implemented):** hour selection is currently **positional** (first *N*
> samples). A **temporal** window — filter samples to `[now, now + N h)` using each sample's
> timestamp — plus a separately configured **fetch horizon** (e.g. 72 h) is logged as a
> future update; it decouples fetch size from the scoring window. See
> `backend/app/risk/session_log.md` (2026-10-15).

**Ownership:** the grid maths, per-cell scoring, snapshot, and the pure "risk at this
point" helper are **Person 2**; the HTTP endpoint that calls it per request is **Person 1**;
snapshot storage and freshness are **Person 4**.

---

## 5. Risk-level bands and severity scale (shared with API.md)

| severity_score | risk_level | badge | Frontend color |
|---|---|---|---|
| ≥ 7.0 | `HIGH` | 🔴 | `#ef4444` |
| 4.0 – 6.9 | `MODERATE` | 🟡 | `#f59e0b` |
| < 4.0 | `LOW` | 🟢 | `#22c55e` |

## 6. Per-zone output shape (extend RiskResult)

`backend/app/risk/classifier.py` produces a dict/`RiskResult` with these keys (v1 keys
**unchanged and required**; new keys **optional-but-recommended** — the `/api/risk-zones`
GeoJSON contract in docs/API.md does not change):

```jsonc
{
  // v1 keys — required, unchanged
  "hazard_id": "…",
  "hazard_type": "rainfall",
  "risk_level": "MODERATE",
  "severity_score": 6.2,
  "affected_area": { "type": "Polygon", "coordinates": […] },   // data-derived (§ 4)
  "calculated_at": "2026-10-09T10:00:00Z",
  "notes": "90 mm/6h above 10-yr return; 1.2M people exposed; flat urban drainage",

  // NEW keys — optional, added by the frontend-facing layer for explainability
  "confidence": "medium",                 // § 6.1
  "lead_time_hours": 24,
  "is_live": true,

  // NEW keys — sub-scores so the UI can show WHY (explainability = trust)
  "hazard_index": 7.8,
  "exposure_index": 6.4,
  "vulnerability_index": 5.1,
  "evidence": [
    "precipitation 28.1 mm/h (heavy, WMO 63)",
    "6h accumulation 91.4 mm exceeds 10-yr return",
    "population raster: 1.2M within zone",
    "mean slope < 1° — poor drainage",
    "confidence: medium (24h forecast, cell spread ±1.8)"
  ]
}
```

### 6.1 Confidence (uncertainty)

| Component | Rule | → confidence |
|---|---|---|
| Lead time | < 12 h forecast | high |
|  | 12–48 h | medium |
|  | > 48 h | low |
| Precipitation probability | ≥ 70% | high |
|  | 40–70% | medium |
|  | < 40% | low |
| Inter-cell spread (std of hazard_index across grid) | ≤ 1.0 | high |
|  | 1.0 – 2.5 | medium |
|  | > 2.5 | low |

Final = worst (lowest) of the three. A `HIGH` risk zone with `confidence: low`
renders identically to `HIGH` today but the UI badge says *"HIGH — low confidence"*.

---

## 7. Exposure & vulnerability (data feeds, prioritized)

| Priority | Feed | Used for | Source | Format | Cost |
|---|---|---|---|---|---|
| 1 | Population raster | `exposure_index` | WorldPop (~100 m resolution) | GeoTIFF → bin to grid cells | free/CC-BY |
| 2 | Terrain slope (DEM) | `vulnerability_index` | Copernicus GLO-30 (30 m) | GeoTIFF → mean slope per cell | free |
| 3 | Soil moisture + past accumulation | context/antecedent | Open-Meteo `soil_moisture_*`, `past_days` | JSON | free |
| 4 | Land use / urban imperviousness | `vulnerability_index` | OSM landuse / local open data | GeoJSON | free |
| 5 | Flood risk history (local) | calibration + priors | municipal open data / news archive | CSV/GeoJSON | varies |

Exposure/vulnerability are 0–10 indices computed per grid cell **once** (cached as derived
rasters; they change slowly). Runtime risk then re-scales fast. Do **not** fetch rasters on
every hazard request.

> **WORKING ASSUMPTION**: raster-to-cell aggregation (population weighted mean vs. max)
> is a per-region choice (see § 10) until calibration.

---

## 8. Calibration / verification (the trust engine)

Goal: a track record. Every issued risk claim is stored; later compared to what actually
happened (Open-Meteo **archive** API, free, 80 years). New DB table (suggested for Person 4):

```sql
CREATE TABLE IF NOT EXISTS risk_predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hazard_id TEXT,                 -- nullable: group for same event
    region TEXT NOT NULL,           -- pilot region key
    issued_at TEXT NOT NULL,        -- when claim was made
    forecast_time TEXT NOT NULL,    -- target hour of the forecast
    predicted_risk_level TEXT NOT NULL,   -- HIGH/MODERATE/LOW
    severity_score REAL,
    observed_rainfall_mm REAL,      -- backfilled from archive
    verified BOOLEAN DEFAULT 0
);
```

After ~N target-hours, backfill `observed_rainfall_mm`, classify outcome, and build the 2×2:

| | Event occurred (obs ≥ threshold) | No event |
|---|---|---|
| **forecast HIGH** | hit | false alarm |
| **forecast ≤ MOD** | miss | correct rejection |

Metrics to display on the portal (define thresholds in § 10):
**POD** (probability of detection), **FAR** (false-alarm ratio), **CSI** (critical success index).

---

## 9. Working-assumption policy

- Every threshold/parameter without a citable source carries an explicit
  `> **WORKING ASSUMPTION**` note with: value, reason, replacement plan.
- Calibration (§ 8) is the *mechanism* that replaces assumptions with evidence.
- Nothing labelled a working assumption may be presented in the UI as a factual certainty.

## 10. Open decisions (to be closed via PRs, one row each)

| # | Decision | Owner | Target |
|---|---|---|---|
| 1 | `weather → rainfall` hazard_type mapping | P1 + P2 | before wiring |
| 2 | ~~Polygon method: union-of-buffers vs convex hull~~ **CLOSED** — rainfall geometry = grid cells (no buffers/hull/circle), § 4 | P2 | done |
| 3 | Event-local grid spacing per region | P2 | Ph2 |
| 4 | Earthquake GMPE selection (spec drafted in § 12) | P2 | Ph2 |
| 5 | Raster aggregation rule | P2 | Ph2 |
| 6 | POD/FAR/CSI threshold targets | P1 + P2 | Ph4 |
| 7 | Regional-grid cell size + peak-hour window (§ 4.1) | P1 + P2 | before grid serving |

## 11. Implementation phases (each independently shippable & honest)

| Phase | Scope | Exit criteria | Effort |
|---|---|---|---|
| **P0** | Contract: mapping decision, RISK_MODEL filled, tests for existing engine | `classify()` reachable from real `weather` records; ≥ 5 engine tests; docs updated | days |
| **P1** | Multi-cell grid → data-derived footprint (§ 4) | `affected_area` derived from grid cells; circle only as labelled fallback | days–1 wk |
| **P2** | Exposure + vulnerability rasters (§ 7); sub-scores + evidence in output | severity_score breaks down into 3 indices; zone card explainable | 1–2 wk |
| **P3** | Return-period tables; antecedent soil moisture (§ 3.4, § 7-3) | evidence strings cite return levels | 1–2 wk |
| **P4** | Calibration store + archive backfill + metrics (§ 8) | portal shows POD/FAR/CSI for pilot region | 1 wk |

Nothing in this document is "all-or-nothing": each phase ships alone, adds trust, and is
verifiable. The **pilot-region constraint applies to all phases** — never scale wide before
P4 has verified one region.

---

## 12. Earthquake (USGS) — specification (draft)

> Status: **SPECIFICATION DRAFT (2026-10-13).** Threshold framework proposed; the
> ground-motion attenuation relation (GMPE) is **not yet selected**, so the mapping
> below is preliminary and must be finalised (with a cited GMPE) before any code.
> No earthquake classification is implemented yet.

### 12.1 Data source and geographic scope

- **Source:** USGS earthquake feed (GeoJSON, no API key required).
- **Scope:** USGS is a **global** catalog. SafeGrid filters to an **India bounding box** — latitude `6–38`, longitude `68–98` (includes mainland India + Andaman & Nicobar). Events outside the box are ignored.
- **Why a GMPE, not a fixed radius:** a fixed-radius buffer around the epicenter is an oversimplification — shaking decays with distance *and* depth, and large events rupture over a fault of non-trivial length. SafeGrid instead derives shaking **intensity** from a published ground-motion relation.

### 12.2 Input parameters

| Parameter | USGS source | Required? | Notes |
|---|---|---|---|
| `magnitude` | `properties.mag` (the **preferred** magnitude) | yes | See § 12.3 — no scale conversion. |
| `mag_type` | `properties.magType` | yes (metadata) | e.g. `mww`, `mw`, `mb`, `ml`. Passed through; drives the confidence flag. |
| `depth_km` | `geometry.coordinates[2]` | yes | Hypocentral depth. |
| `latitude` / `longitude` | `geometry.coordinates[1]` / `[0]` | yes | Epicenter. |
| `time` | `properties.time` | yes | Event origin time. |
| `mmi`, `cdi`, `alert`, `tsunami`, `felt`, `sig`, `place` | `properties.*` | optional | Compounding context only; not required for base classification. |

**Internal representation (must match the shared models).** SafeGrid's `DataRecord` and `Hazard` models (`backend/app/models/data.py`, `models/hazard.py`) carry only **`magnitude`** as a first-class hazard field — alongside `id`, `data_type` (mapped to `hazard_type`), `source`, `timestamp`, `location`, and `probability`. Everything else in the table above — `mag_type`, `depth_km`, and every optional `properties.*` value — travels inside **`specific_data`** (a free-form dict), exactly as rainfall carries `precipitation_mm`, `wind_speed_kmh`, and `weather_code`. `identify_hazard()` copies `specific_data` through unchanged, so `earthquake.py` must extract `mag_type`/`depth_km` from `specific_data` the same way `rain.py` extracts its precipitation fields. **No model change is required**, and Person 1's USGS adapter should emit `DataRecord(data_type="seismic", …)` (not `Hazard`) to stay on the shared 3-tier flow.

### 12.3 Magnitude scale decision (LOCKED)

- **Standardise on the USGS preferred magnitude.** Do **not** convert between scales (`ml`, `mb`, `ms`, `mww`, …) — they are not mutually convertible, and conversion would fabricate precision.
- **"Richter" is not used.** The formal Richter scale is **local magnitude (ML)**: USGS only reports it (`magType = "ml"`) for a subset of small regional events, and **ML saturates around ~M6.5–7** — exactly the range SafeGrid cares about. Moment magnitude (`mw`/`mww`) is the modern standard and the correct input to attenuation relations.
- **Non-mw-family `magType`:** classify anyway, but record a **low-confidence** note in `RiskResult.notes`. Never convert, never drop the event.

### 12.4 Thresholds — intensity (MMI) based — ⚠️ PRELIMINARY

Shaking **intensity** (Modified Mercalli Intensity, MMI) is derived from the GMPE, then banded into SafeGrid's three risk levels. MMI is a *qualitative intensity* scale describing observed effects, distinct from the magnitude (energy) of an event.

- **GMPE selection: 🔴 NOT YET DECIDED.** Candidate: **USGS ShakeMap `Worden et al. (2012)` MMI relation** (inputs: magnitude, depth, hypocentral distance), or an India-region relation. The chosen relation's coefficients, source, and regional limitations **must** be cited here before implementation.
- Ring radii are the GMPE's **iso-intensity contour distances** (see § 12.5) — **not** invented steps.
- Hypocentral distance used throughout: `d_hypo = sqrt(d_epi² + depth²)`.

Proposed mapping (severity 0.0–10.0), to be confirmed with the GMPE:

| Risk Level | MMI (shaking) | Severity Score | Justification | Source | Known Limitations |
|---|---|---|---|---|---|
| **🟢 LOW** | `I – III` | `0.0 – 3.9` | *Not felt* to *weak*. Felt by few at rest; hanging objects swing. No built-environment damage. | Modified Mercalli Intensity (MMI) scale | Intensity is felt/perception-based; sparse reporting in low-population areas. |
| **🟡 MODERATE** | `IV – V` | `4.0 – 6.9` | *Light* to *moderate*. Felt widely; windows/dishes rattle; some breakage of fragile objects. | Modified Mercalli Intensity (MMI) scale | Poorly-reporting regions may under-represent felt intensity. |
| **🔴 HIGH** | `VI – VIII` | `7.0 – 9.4` | *Strong* to *severe*. Felt by all; slight damage in well-built structures, considerable in weak ones; possible utility disruption. | Modified Mercalli Intensity (MMI) scale | Structural vulnerability differs by construction type; not modelled here. |
| **🔴 HIGH** | `IX +` | `9.5 – 10.0` | *Violent* to *extreme*. Considerable to total damage; ground deformation possible. | Modified Mercalli Intensity (MMI) scale | Rare; forecast uncertainty high; local site amplification not modelled. |

### 12.5 Affected area computation — concentric intensity rings

- **Geographic model:** concentric GeoJSON rings (i.e. a `MultiPolygon`, one polygon per intensity band) centred on the epicenter, drawn at the **MMI contour distances from the GMPE**.
- **Radial decay is real physics:** for an event source, intensity decreases with hypocentral distance along the selected attenuation relation — a grid is the wrong tool for an event.
- **Coordinate order:** RFC 7946 GeoJSON — `[longitude, latitude]`.
- **Known limitations:**
  - **Point-source approximation:** for large events (`M ≥ ~6.5`) the rupture length is non-negligible; a point source underestimates near-field extent. (Future: extended-source / rupture-length models.)
  - **No site amplification:** local soil/rock conditions modify shaking and are not modelled.
  - **GMPE regionality:** relations are calibrated for specific tectonic regions — using a non-India relation is an approximation that must be stated.

### 12.6 Compounding / contextual factors

- `tsunami` flag, `depth_km`, and coastal proximity feed the **secondary tsunami hazard** (see `secondary.py` specification, pending) — **not** the shaking score. Secondary hazards are deliberately kept separate from the primary severity.
- `alert` / `sig` (USGS PAGER) may be surfaced as context but are not used to alter the MMI-derived score.

---

## Change log

| Date | Change | Author |
|---|---|---|
| 2026-10-06 | Initial placeholder scaffold | scaffold |
| 2026-10-08 | Documented rainfall/weather thresholds, compounding factors, and affected-area scaling (justifications moved from `rain.py`) | Person 2 |
| 2026-10-11 | Switched hourly bands to IMD spell-rate (10/20/30/50/100 mm/h); attributed hourly and 24-hour bands to IMD; full WMO weather-code table (incl. 97) | Person 2 |
| 2026-10-11 | Added provider `data_type` → `hazard_type` mapping (`weather`→`rainfall`, `seismic`→`earthquake`); `identify_hazard()` skips unmapped labels | Person 2 |
| 2026-10-11 | v2 spec: risk framework, data-derived footprint, confidence, exposure/vulnerability, calibration plan | Person 1 |
| 2026-10-13 | Merge resolution: v2 framework kept as backbone; adopted IMD rainfall thresholds (matches `rain.py`); data-derived grid footprint supersedes the v1 radius-from-score rule | Person 1 |
| 2026-10-13 | Replace earthquake placeholder with a specification draft: USGS input contract, India bbox scope, locked no-conversion magnitude decision (Richter/ML rejected), MMI-based threshold framework, concentric-ring affected area. **GMPE still unselected; no code.** | Person 2 |
| 2026-10-15 | Merge of `feature/data-ingestion` into `feature/risk-engine`: kept Person 1's v2 framework; re-applied Person 2's earthquake spec as § 12; pointer fixes in § 4 / § 10 | Person 2 |
| 2026-10-15 | Added § 4.1 regional risk grid (precomputed snapshot → point lookup): region-agnostic config grid, peak-hour scoring, out-of-grid ≠ LOW, user-facing output = level + polygon + computed_at; open decision 7 (cell size + window) | Person 2 |
| 2026-10-15 | Rain geometry switched to the grid: § 4 rewritten — rainfall affected area = the grid cell (square), `compute_rainfall_polygon` removed, no circle fallback; circles are earthquake-only (§ 12). Decision 2 closed | Person 2 |
| 2026-10-19 | § 4.1: documented how a region is chosen — a granted location becomes a box either explicitly or via a **declared coverage radius** (`region_around(lat, lon, radius_km)`), centre winning when both are set. Radius is a coverage parameter, not a risk threshold; it yields the **bounding box of square cells, never a circle** (§ 4 rule respected). Village boundaries deliberately unused: OSM outlines are too patchy across rural Karnataka to trust, and a wrong outline would score the wrong ground while looking authoritative | Person 1 |
| 2026-10-19 | § 4.1: noted that serving may **score an unstored square on demand** (same `score_grid()`, sampled at the cell centre) so a snapshot lookup is no longer the only path to an answer. No thresholds, bands or severity scale changed | Person 1 |