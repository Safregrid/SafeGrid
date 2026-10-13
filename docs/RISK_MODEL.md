# SafeGrid — Risk Model

> Status: **Rainfall implemented (Person 2, 2026-10-08); Earthquake specification drafted (Person 2, 2026-10-13) — GMPE still unselected, no earthquake code yet.**
> Branch: `feature/risk-engine`

---

## Structure

For each hazard type, document:

1. **Hazard name**
2. **Data source** (e.g. USGS, Open-Meteo)
3. **Input parameter** (e.g. magnitude, precipitation mm/h)
4. **Thresholds**
5. **Affected area computation** — describe how the geographic polygon is derived.

---

## Earthquake (USGS)

> Status: **SPECIFICATION DRAFT (2026-10-13).** Threshold framework proposed; the
> ground-motion attenuation relation (GMPE) is **not yet selected**, so the mapping
> below is preliminary and must be finalised (with a cited GMPE) before any code.
> No earthquake classification is implemented yet.

### 1. Data Source and Geographic Scope

- **Source:** USGS earthquake feed (GeoJSON, no API key required).
- **Scope:** USGS is a **global** catalog. SafeGrid filters to an **India bounding box** — latitude `6–38`, longitude `68–98` (includes mainland India + Andaman & Nicobar). Events outside the box are ignored.
- **Why a GMPE, not a fixed radius:** a fixed-radius buffer around the epicenter is an oversimplification — shaking decays with distance *and* depth, and large events rupture over a fault of non-trivial length. SafeGrid instead derives shaking **intensity** from a published ground-motion relation.

### 2. Input Parameters

| Parameter | USGS source | Required? | Notes |
|---|---|---|---|
| `magnitude` | `properties.mag` (the **preferred** magnitude) | yes | See §3 — no scale conversion. |
| `mag_type` | `properties.magType` | yes (metadata) | e.g. `mww`, `mw`, `mb`, `ml`. Passed through; drives the confidence flag. |
| `depth_km` | `geometry.coordinates[2]` | yes | Hypocentral depth. |
| `latitude` / `longitude` | `geometry.coordinates[1]` / `[0]` | yes | Epicenter. |
| `time` | `properties.time` | yes | Event origin time. |
| `mmi`, `cdi`, `alert`, `tsunami`, `felt`, `sig`, `place` | `properties.*` | optional | Compounding context only; not required for base classification. |

**Internal representation (must match the shared models).** SafeGrid's `DataRecord` and `Hazard` models (`backend/app/models/data.py`, `models/hazard.py`) carry only **`magnitude`** as a first-class hazard field — alongside `id`, `data_type` (mapped to `hazard_type`), `source`, `timestamp`, `location`, and `probability`. Everything else in the table above — `mag_type`, `depth_km`, and every optional `properties.*` value — travels inside **`specific_data`** (a free-form dict), exactly as rainfall carries `precipitation_mm`, `wind_speed_kmh`, and `weather_code`. `identify_hazard()` copies `specific_data` through unchanged, so `earthquake.py` must extract `mag_type`/`depth_km` from `specific_data` the same way `rain.py` extracts its precipitation fields. **No model change is required**, and Person 1's USGS adapter should emit `DataRecord(data_type="seismic", …)` (not `Hazard`) to stay on the shared 3-tier flow.

### 3. Magnitude Scale Decision (LOCKED)

- **Standardise on the USGS preferred magnitude.** Do **not** convert between scales (`ml`, `mb`, `ms`, `mww`, …) — they are not mutually convertible, and conversion would fabricate precision.
- **"Richter" is not used.** The formal Richter scale is **local magnitude (ML)**: USGS only reports it (`magType = "ml"`) for a subset of small regional events, and **ML saturates around ~M6.5–7** — exactly the range SafeGrid cares about. Moment magnitude (`mw`/`mww`) is the modern standard and the correct input to attenuation relations.
- **Non-mw-family `magType`:** classify anyway, but record a **low-confidence** note in `RiskResult.notes`. Never convert, never drop the event.

### 4. Thresholds — Intensity (MMI) based — ⚠️ PRELIMINARY

Shaking **intensity** (Modified Mercalli Intensity, MMI) is derived from the GMPE, then banded into SafeGrid's three risk levels. MMI is a *qualitative intensity* scale describing observed effects, distinct from the magnitude (energy) of an event.

- **GMPE selection: 🔴 NOT YET DECIDED.** Candidate: **USGS ShakeMap `Worden et al. (2012)` MMI relation** (inputs: magnitude, depth, hypocentral distance), or an India-region relation. The chosen relation's coefficients, source, and regional limitations **must** be cited here before implementation.
- Ring radii are the GMPE's **iso-intensity contour distances** (see §5) — **not** invented steps.
- Hypocentral distance used throughout: `d_hypo = sqrt(d_epi² + depth²)`.

Proposed mapping (severity 0.0–10.0), to be confirmed with the GMPE:

| Risk Level | MMI (shaking) | Severity Score | Justification | Source | Known Limitations |
|---|---|---|---|---|---|
| **🟢 LOW** | `I – III` | `0.0 – 3.9` | *Not felt* to *weak*. Felt by few at rest; hanging objects swing. No built-environment damage. | Modified Mercalli Intensity (MMI) scale | Intensity is felt/perception-based; sparse reporting in low-population areas. |
| **🟡 MODERATE** | `IV – V` | `4.0 – 6.9` | *Light* to *moderate*. Felt widely; windows/dishes rattle; some breakage of fragile objects. | Modified Mercalli Intensity (MMI) scale | Poorly-reporting regions may under-represent felt intensity. |
| **🔴 HIGH** | `VI – VIII` | `7.0 – 9.4` | *Strong* to *severe*. Felt by all; slight damage in well-built structures, considerable in weak ones; possible utility disruption. | Modified Mercalli Intensity (MMI) scale | Structural vulnerability differs by construction type; not modelled here. |
| **🔴 HIGH** | `IX +` | `9.5 – 10.0` | *Violent* to *extreme*. Considerable to total damage; ground deformation possible. | Modified Mercalli Intensity (MMI) scale | Rare; forecast uncertainty high; local site amplification not modelled. |

### 5. Affected Area Computation — Concentric Intensity Rings

- **Geographic model:** concentric GeoJSON rings (i.e. a `MultiPolygon`, one polygon per intensity band) centred on the epicenter, drawn at the **MMI contour distances from the GMPE**.
- **Radial decay is real physics:** for an event source, intensity decreases with hypocentral distance along the selected attenuation relation — a grid is the wrong tool for an event.
- **Coordinate order:** RFC 7946 GeoJSON — `[longitude, latitude]`.
- **Known limitations:**
  - **Point-source approximation:** for large events (`M ≥ ~6.5`) the rupture length is non-negligible; a point source underestimates near-field extent. (Future: extended-source / rupture-length models.)
  - **No site amplification:** local soil/rock conditions modify shaking and are not modelled.
  - **GMPE regionality:** relations are calibrated for specific tectonic regions — using a non-India relation is an approximation that must be stated.

### 6. Compounding / Contextual Factors

- `tsunami` flag, `depth_km`, and coastal proximity feed the **secondary tsunami hazard** (see `secondary.py` specification, pending) — **not** the shaking score. Secondary hazards are deliberately kept separate from the primary severity.
- `alert` / `sig` (USGS PAGER) may be surfaced as context but are not used to alter the MMI-derived score.

---

## Rainfall / Weather (Open-Meteo)

### 1. Input Parameters

Normalized from the Open-Meteo hourly weather feed:
- `precipitation_mm`: Precipitation rate (mm/h) or 24-hour accumulation (mm/24h).
- `time_window_hours`: Assessment window (`1` for instantaneous hourly rate, `24` for cumulative rainfall).
- `wind_speed_kmh` & `wind_gusts_kmh`: Secondary compounding wind parameters (km/h).
- `weather_code`: WMO weather interpretation code (e.g. convective storms, thunderstorms).
- `precipitation_probability`: Probability score (0–100%) indicating forecast confidence.

### 2. Hourly Precipitation Thresholds (Window = 1 Hour)

The hourly intensity bands follow the **India Meteorological Department (IMD)** rainfall *spell-rate* classification. IMD expresses hourly intensity as a spell rate in cm/h; converted to mm/h (1 cm = 10 mm):

| Risk Level | Precipitation Rate | Severity Score | Justification | Source | Known Limitations |
|---|---|---|---|---|---|
| **🟢 LOW** | `< 10 mm/h` | `0.0 – 3.9` | IMD **Light spell** (< 1 cm/h). Standard municipal drainage absorbs runoff. | India Meteorological Department (IMD) | Localized clogged drains or poor urban topography may still produce minor pooling. |
| **🟡 MODERATE** | `10 – 20 mm/h` | `4.0 – 6.9` | IMD **Moderate spell** (1–2 cm/h). Runoff accumulates on roadways; drainage systems under moderate loading. | India Meteorological Department (IMD) | Ground saturation prior to rainfall not accounted for without soil moisture data. |
| **🔴 HIGH** | `20 – 30 mm/h` | `7.0 – 8.4` | IMD **Intense spell** (2–3 cm/h). Significant surface water accumulation and localized flooding. | India Meteorological Department (IMD) | Duration of intensity is crucial; brief bursts differ from sustained downpours. |
| **🔴 HIGH** | `30 – 50 mm/h` | `8.5 – 9.4` | IMD **Very intense spell** (3–5 cm/h). High risk of waterlogging and grid disruption. | India Meteorological Department (IMD) | Runoff velocity depends on slope and urban impermeability. |
| **🔴 HIGH** | `50 – 100 mm/h` | `9.5 – 10.0` | IMD **Extremely intense spell** (5–10 cm/h). Severe flash-flood and infrastructure risk. | India Meteorological Department (IMD) | Real-time gauge/radar data needed to distinguish intense bursts from sustained rates. |
| **🔴 HIGH (Cloudburst)** | `> 100 mm/h` | `10.0` | IMD **Cloudburst** (> 10 cm/h). Extreme flash-flood potential. | India Meteorological Department (IMD) | Cloudbursts are highly localized; forecast grid resolution may miss peak intensity. |

### 3. 24-Hour Accumulated Rainfall Thresholds (Window = 24 Hours)

The 24-hour accumulation bands follow the **India Meteorological Department (IMD)** official rainfall classification (Light `2.5–15.5 mm`, Moderate `15.6–64.4 mm`, Heavy `64.5–115.5 mm`, Very Heavy `115.6–204.4 mm`, Extremely Heavy `≥ 204.5 mm`). SafeGrid maps the upper IMD bands onto its three-level scheme: IMD *Light* → 🟢 LOW, IMD *Moderate* → 🟡 MODERATE, IMD *Heavy* → 🔴 HIGH, IMD *Very Heavy* / *Extremely Heavy* → 🔴 HIGH.

| Risk Level | Accumulation (mm/24h) | Severity Score | Justification | Source |
|---|---|---|---|---|
| **🟢 LOW** | `< 15.5 mm` | `0.0 – 3.9` | Light rainfall. Insignificant catchment saturation. | India Meteorological Department (IMD) / NOAA standards |
| **🟡 MODERATE** | `15.5 – 64.4 mm` | `4.0 – 6.9` | Moderate rainfall. Prolonged soaking leads to rising water tables and localized pooling. | India Meteorological Department (IMD) standard rainfall criteria |
| **🔴 HIGH** | `64.5 – 115.5 mm` | `7.0 – 8.4` | Heavy rainfall. High likelihood of regional waterlogging and drainage overwhelm. | India Meteorological Department (IMD) heavy rainfall classification |
| **🔴 HIGH (Very Heavy)**| `> 115.5 mm` | `8.5 – 10.0` | Very heavy to extremely heavy rainfall. Severe flood inundation potential. | India Meteorological Department (IMD) very heavy rainfall classification |

### 4. Compounding Factors

Precipitation does not act in isolation. The risk engine applies compounding modifiers:
- **Wind Hazards**:
  - Sustained winds $\ge 50\text{ km/h}$ or gusts $\ge 65\text{ km/h}$: Adds `+1.5` to severity score to account for downed tree limbs, severed power lines, and blocked storm drains.
  - Gusts $\ge 45\text{ km/h}$ or sustained $\ge 35\text{ km/h}$: Adds `+0.8` to severity score.
- **Convective Thunderstorms (WMO Codes)**:
  - Codes `95`, `96`, `99` (Thunderstorms with/without hail): Impose an absolute **HIGH risk floor** ($\text{severity} \ge 7.0$).
  - Code `82` (Violent rain showers): Imposes a **HIGH risk floor** ($\text{severity} \ge 7.0$).
- **Precipitation Probability**:
  - Probability $< 40\%$ when rain is forecast flags high forecast uncertainty in diagnostic factors.

### 5. Affected Area Computation

- **Geographic Model**: Closed GeoJSON `Polygon` representing the localized precipitation catchment and runoff footprint around the forecast point `[longitude, latitude]`.
- **Scaling Rule**:
  - $\text{Score} < 4.0$ (Low): Radius $3.0\text{ km} - 5.0\text{ km}$ (localized shower / numerical grid cell footprint).
  - $4.0 \le \text{Score} < 7.0$ (Moderate): Radius $5.0\text{ km} - 10.0\text{ km}$ (catchment runoff and waterlogging zone).
  - $\text{Score} \ge 7.0$ (High): Radius $10.0\text{ km} - 20.0\text{ km}$ (severe convective storm cell and regional flash-flood basin).
- **Coordinate Order**: RFC 7946 GeoJSON format: `[longitude, latitude]`.

---

## Mandatory Rule

Green / Low Risk indicates low hazard relative to threshold; it must **NEVER** be described as absolute safety.

---

## Change log

| Date | Change | Author |
|---|---|---|
| 2026-10-08 | Document rainfall/weather thresholds, compounding factors, and affected-area scaling (justifications moved from `rain.py`) | Person 2 |
| 2026-10-11 | Switch hourly bands to IMD spell-rate classification (10/20/30/50/100 mm/h); attribute 24-hour bands to IMD; expand weather-code table to the full WMO WW set (incl. code 97) | Person 2 |
| 2026-10-11 | Add provider `data_type` → canonical `hazard_type` mapping (`weather`→`rainfall`, `seismic`→`earthquake`); `identify_hazard()` skips unmapped labels. Pushed `classifier.py` + `rain.py` + this doc | Person 2 |
| 2026-10-13 | Replace earthquake placeholder with a specification draft: USGS input contract, India bbox scope, locked no-conversion magnitude decision (Richter/ML rejected), MMI-based threshold framework, concentric-ring affected area. **GMPE still unselected; no code.** | Person 2 |
