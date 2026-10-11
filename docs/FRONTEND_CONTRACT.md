# SafeGrid — Frontend Contract (for Person 3 + frontend AI agents)

> **Read this file FIRST, before writing or modifying any frontend code.**
> If you are an AI agent assisting Person 3, this file is your specification.
> **If any field here differs from `docs/API.md` or the backend models, the backend wins**
> (`backend/app/models/hazard.py` is the source of truth). Raise the difference — do not guess.

Last updated: 2026-10-10

---

## 1. Non-negotiable product rules

These come from `README.md`, `Brain-Part-1/2.md`, and `docs/OFFLINE.md`. Violating them makes the whole project misleading:

1. **SafeGrid is an academic project — NOT an official/government system.**
   - ❌ NEVER render "Disaster Management Authority", "Official Use Only", "SYSTEM ONLINE", "National … Portal", or anything implying government authority.
   - ✅ Honest headers only: e.g. "SafeGrid — hazard risk map (academic project)".
2. **`LOW` / green does NOT mean safe.** Never advertise green as "no risk".
3. **The UI must clearly distinguish live data vs cached/stale data** (see §5).
4. **Risk is computed by the backend only.** The frontend renders risk zones; it never computes risk itself.
5. **All HTTP requests go through `frontend/src/api/client.js`.** Never inline `fetch()` in UI code. Caching logic belongs only in the Service Worker (Person 4).

---

## 2. Data flow the UI must implement

```
GET /api/hazards   → { is_live, hazards[] }      → markers (coordinates + type/source + timestamp)
GET /api/risk-zones → GeoJSON FeatureCollection   → colored polygons (this is where risk lives)
```

- **Markers** = individual hazard events. They have NO risk level, NO severity score.
- **Risk zones** = polygons from the risk engine. They carry `risk_level` and `severity_score`.
- Do not show risk on markers. Do not invent fields to fake it.

---

## 3. Exact API shapes (do not invent fields)

### `GET /api/hazards`

```json
{
  "is_live": true,
  "hazards": [
    {
      "id": "eq-usgs-001",
      "hazard_type": "earthquake",
      "source": "usgs",
      "timestamp": "2026-10-09T10:00:00Z",
      "latitude": 35.6762,
      "longitude": 139.6503,
      "magnitude": 5.4,
      "probability": null,
      "specific_data": { "depth_km": 10.5 },
      "created_at": "2026-10-09T10:01:00Z"
    }
  ]
}
```

**Hazard fields — the complete list. There are NO others.**
`id`, `hazard_type`, `source`, `timestamp`, `latitude`, `longitude`, `magnitude` (nullable), `probability` (nullable, 0–100), `specific_data` (dict), `created_at`.

- ❌ There is **no** `recorded_at`, no per-hazard `risk_level`, no per-hazard `severity_score`, no per-hazard `is_live`.
- The response is always the envelope `{ is_live, hazards }`. Do **not** write code that "handles multiple response formats". There is one format.

### `GET /api/risk-zones`

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "Polygon", "coordinates": [ [ [lon, lat], ... ] ] },
      "properties": {
        "hazard_id": "eq-usgs-001",
        "hazard_type": "earthquake",
        "risk_level": "HIGH",
        "severity_score": 7.2,
        "calculated_at": "2026-10-09T10:00:00Z",
        "is_live": true
      }
    }
  ]
}
```

**Feature `properties` — the complete list. There are NO others.**
`hazard_id`, `hazard_type`, `risk_level`, `severity_score`, `calculated_at`, `is_live`.

### Errors (all endpoints)

```json
{ "detail": "human-readable error message" }
```
Status codes: `200`, `404`, `422`, `500`. Handle non-200 gracefully — show an empty state, never retain stale data as if fresh.

---

## 4. Risk level → color (zones only)

| `risk_level` | Color | Hex |
|---|---|---|
| `HIGH` | red | `#ef4444` |
| `MODERATE` | yellow/amber | `#f59e0b` |
| `LOW` | green | `#22c55e` |

Use a single source of truth for these constants (e.g. export them from the map module). Do not scatter hex values through widget code.

---

## 5. Live vs cached (is_live)

| Signal | Meaning | UI |
|---|---|---|
| live data | fetched successfully just now | green "LIVE" dot |
| cached/stale | served from cache / last-known | orange "CACHED (time)" label with the data age |

- `is_live` arrives on the `/api/hazards` envelope and on each risk-zone feature `properties`.
- If a fetch fails, keep last-known data (from IndexedDB/cache — Person 4's layer) and **show the cached age**. Never pretend cached data is live.

Current contract status (2026-10-10):

- `/api/hazards` and `/api/data` are registered on the backend.
- `/api/risk-zones` is documented but **not yet registered** (backend stub). Handle its absence as an empty state — the map must not crash, and must not fabricate zones.

---

## 6. Required module structure (map/index.js)

`frontend/src/main.js` imports these — **they MUST exist and be exported from `frontend/src/map/index.js`**:

```js
export function initMap(containerId)          // -> maplibregl.Map
export function renderHazardMarkers(map, hazards, onSelectHazard)
export function addRiskZoneLayer(map, featureCollection /* nullable */)
export function updateRiskZones(map, featureCollection)
```

- Color constants (`COLOR_HIGH` / `COLOR_MODERATE` / `COLOR_LOW`) must be **defined** where they are used.
- Referencing a function/variable that does not exist = the build fails. Verify with `npm run build`.
- What each widget does:

| Function | Behavior |
|---|---|
| `initMap` | Create MapLibre map in the container; base stylesheet; no risk logic. |
| `renderHazardMarkers` | Plot hazard events as markers using `latitude`/`longitude`. No fake risk colors on markers. Click → detail card showing `hazard_type`, `source`, `timestamp`, `magnitude`/`probability` if present. |
| `addRiskZoneLayer` | Add (or clear) a GeoJSON polygon layer colored by `properties.risk_level`. Accepts `null` → clears layer. |
| `updateRiskZones` | Replace layer data with a new `FeatureCollection`. |

`main.js` flow (already written — keep it):

```js
import { initMap, renderHazardMarkers, addRiskZoneLayer, updateRiskZones } from './map/index.js';
import { fetchHazards, fetchRiskZones } from './api/client.js';
```

Fetch hazards + risk zones on `map.on('load')`, render both, handle failures with `catch` → empty state (e.g. empty `FeatureCollection`, empty array).

---

## 7. client.js contract

```js
export async function fetchHazards()      // -> Hazard[]  (unwrap data.hazards)
export async function fetchRiskZones()    // -> FeatureCollection | null (null on failure)
```

- Fetch failures: throw or return a nullable/empty value and let callers handle it. Do not swallow errors silently.
- Keep `fetchHazards()` returning the array; the map layer only needs markers.

---

## 8. What offline code NOT to write

- Do NOT implement caching, IndexedDB, or the Service Worker yourself — that is Person 4's subsystem (`frontend/src/offline/`, `frontend/src/service-worker.js`). You may call `getLastKnownRiskZones()` when Person 4 exposes it.
- Do NOT add an `is_live` "offline" feature without coordinating with Person 4 (see `docs/OFFLINE.md`).

---

## 9. ❌ Known mistakes (from review of `feature/frontend-maplibre-ui`) — fix these

1. **Build failure (blocker).** `main.js` imports `initMap`, `addRiskZoneLayer`, `updateRiskZones` which were never exported from `frontend/src/map/index.js`.
   - Fix: implement `initMap`, `addRiskZoneLayer`, `updateRiskZones` in `frontend/src/map/index.js` and export them. Verify `npm run build`.
2. **Undefined color constants.** `COLOR_HIGH`, `COLOR_MODERATE`, `COLOR_LOW` are used but never defined → runtime `ReferenceError`.
   - Fix: define/export them in the map module (§4, §6).
3. **Invented field `recorded_at`.** Not in the Hazard contract. Use `timestamp` / `created_at`.
4. **Per-hazard risk coloring.** `risk_level` on markers always defaults to `LOW` because hazards don't carry risk. Risk comes from `/api/risk-zones` polygons only (§2, §4).
5. **Multi-format guessing in `fetchHazards()`.** The API returns exactly `{ is_live, hazards }`. Also, `is_live` must be surfaced to the UI, not dropped (§3, §5).
6. **Fake government branding.** "SAFEGRID DISASTER MANAGEMENT AUTHORITY", "Official Use Only", "SYSTEM ONLINE", "National … Portal" must be removed (§1, rule 1).
7. **`/api/risk-zones` assumed live.** It is a backend stub today. Build against the agreed shape (§3) and render an empty state when unavailable (§5).
8. **Marker clicks had hardcoded fallbacks.** Requirement: use real `hazard_type`/`source`/`timestamp`; show only real data. Never display made-up telemetry.

---

## 10. Definition of done (P3)

- [ ] `npm run build` passes locally (this is the CI gate).
- [ ] Map renders against the **real** backend (`uvicorn app.main:app` + `npm run dev`).
- [ ] Markers render from `GET /api/hazards` using the exact Hazard fields.
- [ ] Risk zones render from `GET /api/risk-zones` (empty state today) using `risk_level`/`severity_score`.
- [ ] No government/official branding anywhere.
- [ ] All fetches go through `client.js`.
- [ ] Live vs cached is visually distinguishable (green/orange).
- [ ] No invented API fields or response formats.