# SafeGrid — Risk Model

> Status: **Updated for Rainfall by Person 2 (Risk Engine & Geospatial Processing) on 2026-10-08.**
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

## Earthquake (USGS) — PLACEHOLDER

> Person 2 will document and implement earthquakes in a separate file/module.

Input: Richter magnitude from USGS feed.

Thresholds: **NOT YET DECIDED.**

Affected area: **NOT YET DECIDED.** Options include fixed-radius buffer (oversimplification) or felt-intensity contours (more accurate but harder). Document the choice and tradeoffs.

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
