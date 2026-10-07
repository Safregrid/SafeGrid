# SafeGrid — Architecture

> Last updated: 2026-10-06
> Status: initial scaffold — decisions are recorded as DECIDED or OPEN.

---

## 1. System overview

```
                    PUBLIC APIs
                        │
          ┌─────────────┼─────────────┐
          ↓             ↓             ↓
        USGS        Open-Meteo    (future)
          │             │             │
          └─────────────┼─────────────┘
                        ↓
                 FastAPI Backend
                        ↓
                 Data Normalization
                        ↓
                     Risk Engine
                        ↓
                      GeoJSON
                        ↓
                     REST API
                        ↓
                     PWA Client
                        ↓
                     MapLibre
                        ↓
                  🔴 🟡 🟢 Zones
```

The backend is the **single source of truth** for risk calculations.
The frontend visualizes and interacts with backend results only.

---

## 2. Subsystem ownership

### Person 1 — Backend / API integration
**Directory:** `backend/app/`

Owns:
- FastAPI application entry point
- External API adapters (USGS, Open-Meteo)
- Data normalization into the internal `Hazard` model
- REST endpoint definitions
- Backend/database integration layer

Key files:
- `backend/app/main.py` — FastAPI app + router registration
- `backend/app/api/` — route handlers
- `backend/app/ingestion/` — external API clients
- `backend/app/models/` — internal data schemas (Pydantic)

### Person 2 — Risk engine / Geospatial processing
**Directory:** `backend/app/risk/`

Owns:
- Risk classification rules
- Hazard-specific severity calculations
- Affected-area geometry logic
- GeoJSON generation
- Unit tests for all risk calculations

Key files:
- `backend/app/risk/classifier.py` — risk level assignment
- `backend/app/risk/geometry.py` — geographic area computation
- `backend/tests/test_risk/` — risk unit tests

### Person 3 — Frontend / Map
**Directory:** `frontend/`

Owns:
- PWA application shell
- MapLibre GL JS integration
- GeoJSON layer rendering (🔴🟡🟢 zones)
- Hazard marker display
- Dashboard UI

Key files:
- `frontend/src/map/` — MapLibre setup and layer management
- `frontend/src/api/` — fetch wrappers for backend REST API
- `frontend/public/manifest.json` — PWA manifest

### Person 4 — Database / Offline
**Directory:** `backend/app/db/`, `frontend/src/offline/`

Owns:
- Database schema and migrations
- SQLAlchemy models / database session management
- Service Worker
- Cache Storage strategy
- IndexedDB / local storage for last-known hazard data
- Offline/online state management

Key files:
- `backend/app/db/` — database models and session
- `frontend/src/service-worker.js` — Service Worker
- `frontend/src/offline/` — offline data management

---

## 3. Subsystem interfaces

These are the contracts between subsystems. Each must be agreed on before integration.

### Interface A — Ingestion → Risk engine (internal Python)

Person 1 normalizes external API responses into a `Hazard` object.
Person 2 consumes a `Hazard` object and returns a `RiskResult` object.

```
Hazard {
    hazard_type: str        # "earthquake" | "rainfall" | ...
    source: str             # "usgs" | "open_meteo"
    timestamp: datetime
    location: Point         # GeoJSON Point (lon, lat)
    raw_magnitude: float | None
    raw_values: dict        # source-specific normalized fields
}

RiskResult {
    hazard_id: str
    risk_level: str         # "HIGH" | "MODERATE" | "LOW"
    severity_score: float
    affected_area: GeoJSON  # Polygon or FeatureCollection
    calculated_at: datetime
    notes: str | None       # threshold justification reference
}
```

> ⚠️ OPEN: exact fields are not finalized. Both Person 1 and Person 2 must agree before implementing.

### Interface B — Backend REST API → Frontend (HTTP/JSON)

Defined in `docs/API.md`.

Key endpoints (initial, not final):

```
GET /api/hazards          → list of current normalized hazards
GET /api/hazards/{id}     → single hazard detail
GET /api/risk-zones       → GeoJSON FeatureCollection of risk zones
GET /health               → backend health check
```

> ⚠️ OPEN: exact request/response schema is not finalized. Update API.md when agreed.

### Interface C — Backend → Database (internal Python)

Person 1 writes normalized hazards.
Person 4 owns the schema, migrations, and ORM models.
Person 1 calls Person 4's repository functions — not raw SQL.

### Interface D — Frontend API client → Service Worker (browser)

Person 3 fetches from the backend via a thin API client module.
Person 4's Service Worker intercepts fetch events and applies caching strategy.
The frontend must not embed caching logic itself.

---

## 4. Technology decisions

| Decision | Status | Choice |
|---|---|---|
| Backend language | DECIDED | Python |
| Backend framework | DECIDED | FastAPI |
| Frontend type | DECIDED | PWA |
| Map library | DECIDED | MapLibre GL JS |
| Initial hazard sources | DECIDED | USGS, Open-Meteo |
| Version control | DECIDED | Git / GitHub |
| LLM / AI features | DECIDED (excluded) | Not in MVP |
| SMS / WhatsApp | DECIDED (excluded) | Not in MVP |
| Flutter client | DECIDED (deferred) | Not in MVP |
| Database | **OPEN** | Not yet chosen |
| Hosting / deployment | **OPEN** | Not yet chosen |
| GeoJSON method per hazard | **OPEN** | Decided per hazard type |
| Risk thresholds | **OPEN** | To be justified with references |
| Notification mechanism | **OPEN** | Not in MVP |

---

## 5. Risk engine — design constraint

Every risk threshold must be documented with:

1. What the threshold represents
2. Why it was selected
3. Source or reference
4. Known limitations

Do not invent scientifically meaningful thresholds to make demos look good.
See `docs/RISK_MODEL.md`.

---

## 6. Offline strategy

Online: fresh hazard data, risk recalculation, full sync.
Offline: cached app shell, emergency instructions, emergency contacts, last-known hazard/risk data.

The UI must clearly distinguish **live data** from **cached/stale data**.

A PWA cannot receive new data from internet APIs while completely offline.

See `docs/OFFLINE.md`.

---

## 7. Change log

| Date | Decision | Previous | New | Reason |
|---|---|---|---|---|
| 2026-10-06 | Initial scaffold | — | See above | Project start |

When a major architectural decision changes, add a row here and update relevant sections.
