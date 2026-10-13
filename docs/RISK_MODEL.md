# SafeGrid — Risk Model v2

> **Status: DRAFT SPEC (replaces the v1 placeholder)**
> Author: Person 1 (with Person 2 as owner of `backend/app/risk/`).
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

## 4. Hazard — multi-cell footprint (replaces the fabricated circle)

**The affected-area polygon is derived from data, not from a severity score.**
Fabricated circles (`radius = f(score)`, e.g. the v1 3/5/10 km steps) are forbidden
for rainfall risk. Keep `compute_rainfall_polygon` only as an explicit
debug/fallback labelled "approximate".

Algorithm:

1. Around the hazard location, build a **grid of points** (e.g. 7×7 at ~0.2° spacing,
   configurable per region). One Open-Meteo request with comma-separated
   `latitude`/`longitude` arrays (up to 1000 coords) returns per-location results.
2. Compute `hazard_index` per cell (§ 3).
3. Select cells above a threshold (default **≥ MODERATE**, i.e. score ≥ 4.0).
4. Polygon = **union of buffered qualifying cells** (shapely `unary_union`, cell-radius buffer)
   or **convex hull of qualifying centers** — choose one per region, document in § 10.
5. Output: one GeoJSON `Polygon` with the same `risk_zones` feature contract as v1.

> **WORKING ASSUMPTION**: grid spacing, window extent, and cell-buffer radius are calibrated
> per region during § 8. They are not physical boundaries.

**Earthquake (USGS)** stays a **documented fixed-radius attenuation model** (not a circle from
"score"): magnitude → expected felt-intensity attenuation with distance (citable MMI relations).
Exact formula = Person 2 to define in § 10 before implementing.

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
| 2 | Polygon method: union-of-buffers vs convex hull | P2 | Ph2 |
| 3 | Grid spacing / window / buffer radius per region | P2 | Ph2 |
| 4 | Earthquake attenuation formula + radius | P2 | Ph2 |
| 5 | Raster aggregation rule | P2 | Ph2 |
| 6 | POD/FAR/CSI threshold targets | P1 + P2 | Ph4 |

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

## Change log

| Date | Change | Author |
|---|---|---|
| 2026-10-06 | Initial placeholder scaffold | scaffold |
| 2026-10-08 | Documented rainfall/weather thresholds, compounding factors, and affected-area scaling (justifications moved from `rain.py`) | Person 2 |
| 2026-10-11 | Switched hourly bands to IMD spell-rate (10/20/30/50/100 mm/h); attributed hourly and 24-hour bands to IMD; full WMO weather-code table (incl. 97) | Person 2 |
| 2026-10-11 | Added provider `data_type` → `hazard_type` mapping (`weather`→`rainfall`, `seismic`→`earthquake`); `identify_hazard()` skips unmapped labels | Person 2 |
| 2026-10-11 | v2 spec: risk framework, data-derived footprint, confidence, exposure/vulnerability, calibration plan | Person 1 |
| 2026-10-13 | Merge resolution: v2 framework kept as backbone; adopted IMD rainfall thresholds (matches `rain.py`); data-derived grid footprint supersedes the v1 radius-from-score rule | Person 1 |