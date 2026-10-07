# SafeGrid — API Contract

> Status: **DRAFT — schema not yet finalized.**
> Update this document when Person 1, Person 2, and Person 3 agree on the schema.
> Do not treat the examples below as final contracts.

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

### `GET /api/hazards`

Returns the current list of normalized hazard events from all ingested sources.

**Response (draft)**
```json
[
  {
    "id": "string",
    "hazard_type": "earthquake",
    "source": "usgs",
    "timestamp": "2026-01-01T00:00:00Z",
    "location": {
      "type": "Point",
      "coordinates": [lon, lat]
    },
    "raw_magnitude": 5.2,
    "risk_level": "MODERATE"
  }
]
```

> ⚠️ OPEN: field names, types, and included fields are not final.

---

### `GET /api/hazards/{id}`

Returns a single hazard event by ID.

**Path parameters**
- `id` — hazard identifier

**Response (draft)**: same shape as one element of `/api/hazards`.

---

### `GET /api/risk-zones`

Returns a GeoJSON `FeatureCollection` of all current risk zones for map rendering.

Each `Feature` represents a geographic area with a risk level.

**Response (draft)**
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
        "calculated_at": "2026-01-01T00:00:00Z",
        "is_live": true
      }
    }
  ]
}
```

> ⚠️ OPEN: geometry representation per hazard type is not yet decided.
> Do not assume every hazard will use a circular buffer polygon.

---

## Risk levels

| Value | Meaning |
|---|---|
| `"HIGH"` | 🔴 High risk |
| `"MODERATE"` | 🟡 Moderate / potential risk |
| `"LOW"` | 🟢 Low risk |

`LOW` does **not** mean safe. It means the lowest of the three tracked categories.

---

## Error responses

```json
{
  "detail": "human-readable error message"
}
```

Standard HTTP status codes apply (400, 404, 422, 500, 503).

---

## Data freshness

Responses include `is_live: true` when data comes from a live backend fetch.
Responses include `is_live: false` when data is served from cache or last-known state.

The frontend must surface this distinction to users.

---

## Future endpoints (not in MVP)

- `POST /api/reports` — user-submitted local hazard report (P1/P2)
- `GET /api/alerts` — push notification triggers (P1/P2)

---

## Change log

| Date | Change | Author |
|---|---|---|
| 2026-10-06 | Initial draft | scaffold |
