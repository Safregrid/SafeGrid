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

