# SafeGrid — API Contract

> Status: **Updated 2026-10-09** — reflects agreed DataRecord, Hazard, and RiskResult schemas.

---

## Base URL

Development: `http://localhost:8000`

---

## Endpoints

### `GET /health`

Health check. Returns 200 when the backend is running.

**Response**
```json
{
  "status": "ok"
}
```

---

### `GET /api/data`

Returns recent normalized raw environmental observations and forecasts (`DataRecord`) from ingested providers.

**Query parameters**
- `limit` (int, default=50, max=500)

**Response**
```json
{
  "records": [
    {
      "id": "open-meteo:12.9716:77.5946:2026-10-09T10:00",
      "data_type": "weather",
      "source": "open_meteo",
      "timestamp": "2026-10-09T10:00:00Z",
      "latitude": 12.9716,
      "longitude": 77.5946,
      "magnitude": 0.0,
      "probability": 40.0,
      "specific_data": {
        "precipitation_mm": 0.0,
        "wind_speed_kmh": 12.5,
        "wind_gusts_kmh": 22.1,
        "weather_code": 61
      },
      "created_at": "2026-10-09T10:05:00Z"
    }
  ]
}
```

---

### `GET /api/data/{id}`

Returns a single raw data record by ID.

**Path parameters**
- `id` — data record identifier

**Response**: single `DataRecord` object.

---

### `GET /api/hazards`

Returns the current list of identified hazard events.

**Query parameters**
- `limit` (int, default=50, max=500)

**Response**
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
      "specific_data": {
        "depth_km": 10.5
      },
      "created_at": "2026-10-09T10:01:00Z"
    }
  ]
}
```

---

### `GET /api/hazards/{id}`

Returns a single hazard event by ID.

**Path parameters**
- `id` — hazard identifier

**Response**: single `Hazard` object.

---

### `GET /api/risk-zones`

Returns a GeoJSON `FeatureCollection` of all current risk zones for map rendering (main map feed).

Each `Feature` represents a geographic polygon area with a calculated risk level.

**Response**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [...]
      },
      "properties": {
        "hazard_id": "string",
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

---

### `GET /api/risk`

Point lookup into the standing regional grid: "what is the risk at this
coordinate?". Serves the stored `grid_cells` snapshot (see `docs/OFFLINE.md`),
it does not recompute — so the map and the database cannot disagree.

Both `lat` and `lon` are required. Out-of-range values return `422`.

**Exactly three states.** These are deliberately not collapsed into a risk level:

| State | `in_coverage` | `reason` | `risk_level` |
|---|---|---|---|
| A scored cell exists for this point | `true` | `null` | `"HIGH" \| "MODERATE" \| "LOW"` |
| No cell, but inside the configured region | `true` | `"no_data"` | `null` |
| No cell, and outside the configured region | `false` | `"outside_coverage"` | `null` |

**Stored cells decide coverage, not the configured box.** If a square was ever
scored for this point it is served — even if the scheduler has since been
repointed elsewhere — because having scored that square is precisely what *in
coverage* means. One running server can therefore answer for many places. The
configured region only decides what the scheduler refreshes.

Changing `grid_cell_size_deg` describes a different grid, so cells scored at
another size are not found by this endpoint (they remain in the database and
read as `no_data`).

**"Outside coverage" is never served as `"LOW"`.** *We do not model this place*
and *we model it and it is calm* are different claims, and only the second is
evidence. Clients must branch on `reason` before reading `risk_level`.

Returns `200` for all three states: being outside a small pilot region is an
expected condition, not an error.

**Response (a scored cell exists)**
```json
{
  "in_coverage": true,
  "reason": null,
  "cell_id": "grid:0.1:1061:2548",
  "risk_level": "LOW",
  "severity_score": 0.12,
  "affected_area": { "type": "Polygon", "coordinates": [...] },
  "precipitation_mm": 0.3,
  "computed_at": "2026-10-19T13:59:30+00:00",
  "generated_at": "2026-10-19T13:59:30+00:00",
  "is_live": true
}
```

**Response (no stored cell, outside the configured region)**
```json
{
  "in_coverage": false,
  "reason": "outside_coverage",
  "cell_id": null,
  "risk_level": null,
  "severity_score": null,
  "affected_area": null,
  "precipitation_mm": null,
  "computed_at": null,
  "generated_at": null,
  "is_live": false
}
```

Notes:
- `affected_area` is the cell square (GeoJSON `Polygon`). It is named after the
  `grid_cells.affected_area` column; the GeoJSON-spec name `geometry` applies
  only inside a `Feature`, and this response is not a `Feature`.
- Both `generated_at` and `is_live` are exposed, per `docs/OFFLINE.md`. `is_live`
  is derived from `generated_at` against the grid TTL — never hardcoded. A stale
  cell is still served (it is the last known rating), with `is_live: false`.
- `is_live: false` with `reason: "no_data"` means *no data at all*; with a
  `reason` of `null` it means *stale data*. Clients must distinguish.

---

## Risk levels

| Value | Meaning |
|---|---|
| `"HIGH"` | 🔴 High risk zone |
| `"MODERATE"` | 🟡 Moderate / potential risk zone |
| `"LOW"` | 🟢 Low risk zone |

---

## Error responses

```json
{
  "detail": "human-readable error message"
}
```

Standard HTTP status codes apply:
- `200 OK`: Successful response (returns array/dict, even if empty `[]`)
- `404 Not Found`: Invalid resource or hazard ID
- `422 Unprocessable Entity`: Invalid query parameters (e.g. limit < 1)
- `500 Internal Server Error`: Backend/database failure

---

## Data freshness

Responses include `is_live: true` when data comes from live provider ingestion.
Responses include `is_live: false` when data is served from cached or last-known state.

---

## Change log

| Date | Change | Author |
|---|---|---|
| 2026-10-06 | Initial draft | scaffold |
| 2026-10-07 | Aligned Hazard model: `magnitude`, `probability`, `specific_data` | Person 1 |
| 2026-10-09 | Added `GET /api/data` endpoints, 3-tier Data/Hazard/RiskResult model | Person 1 |
| 2026-10-13 | Implemented `GET /api/risk-zones` (persisted risk results as GeoJSON) | Person 1 |
| 2026-10-19 | Implemented `GET /api/risk?lat=&lon=` per the `docs/OFFLINE.md` contract: reads `grid_cells`, three states (`outside_coverage` / `no_data` / scored), `is_live` derived from `generated_at` | Person 1 |
| 2026-10-19 | Coverage now follows the data, not the configured box: a stored cell is served even outside the current region, so one running server answers for many places. `outside_coverage` now means "no cell scored here and outside the region". **Contract change — flagged to Person 4** | Person 1 |

