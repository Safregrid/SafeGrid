# SafeGrid

> Disaster preparedness platform that aggregates public hazard data, processes it through a backend risk engine, and communicates geographic risk through an interactive, offline-capable map.

## Core pipeline

```
External APIs (USGS, Open-Meteo)
        ↓
  FastAPI Backend
        ↓
  Data Normalization
        ↓
    Risk Engine
        ↓
     GeoJSON
        ↓
  REST API  ←─── PWA Client (MapLibre)
                      ↓
               🔴 🟡 🟢 Zones
```

## Technology stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI |
| Frontend | JavaScript/TypeScript, PWA, MapLibre GL JS |
| Hazard data | USGS Earthquake API, Open-Meteo |
| Database | TBD — see [ARCHITECTURE.md](./docs/ARCHITECTURE.md) |
| Version control | Git, GitHub |

## Team ownership

| Person | Subsystem | Branch |
|---|---|---|
| Rajat B R | Backend / API integration | `feature/backend-api` |
| Syed Afroz | Risk engine / Geospatial processing | `feature/risk-engine` |
| Suchith N S| Frontend / Map | `feature/map-ui` |
| S Athreya | Database / Offline | `feature/offline` |

## Quick start

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`.  
API docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`.

## Documentation

- [ARCHITECTURE.md](./docs/ARCHITECTURE.md) — system design decisions
- [API.md](./docs/API.md) — backend/frontend contract
- [RISK_MODEL.md](./docs/RISK_MODEL.md) — risk thresholds and justifications *(placeholder)*
- [OFFLINE.md](./docs/OFFLINE.md) — offline strategy *(placeholder)*

## Important limitations

SafeGrid is an academic project, not a certified emergency-response system.
It does **not** guarantee disaster prediction, official authority, or life-critical reliability.
Offline mode provides access to previously cached data only — it cannot fetch live data without network connectivity.

## Contributing

See [CONTRIBUTING.md](./docs/CONTRIBUTING.md) *(placeholder)*.
