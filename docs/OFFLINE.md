# SafeGrid — Offline Strategy

> Status: **IMPLEMENTED** (Person 4). Covers the MVP scope below.
> Owner: Person 4 (Database & Offline System).

---

## What offline means in SafeGrid

A PWA cannot fetch new data from internet APIs while the device has no network connectivity.

Offline mode in SafeGrid means:
> Continued access to previously cached information, not live disaster detection without communication.

Offline mode **serves cached data only**. It never invents, extrapolates, or estimates data, and cached readings are always labelled with their timestamp.

---

## Offline priorities

1. Application shell (HTML, CSS, JS, fonts) — **done**
2. Last-known hazard list (`/api/hazards`) — **done**
3. Last-known risk-zone GeoJSON (`/api/risk-zones`) — **done**
4. Emergency instructions / contacts (static content) — **not in MVP**
5. Queued user actions (e.g. local reports) — **out of scope (P1)**

---

## Service Worker strategy

The service worker is bundled with Vite via `vite-plugin-pwa` in **`injectManifest`** mode (`frontend/vite.config.js`, `filename: "service-worker.js"`), so `frontend/src/service-worker.js` is our own source and is registered by `frontend/src/main.js` as `/service-worker.js`.

Cache names are versioned (`offline-v4` → `safegrid-shell-v4` / `safegrid-runtime-v4`); bumping the version in `service-worker.js` retires old caches on activation.

| Resource | Strategy | Reason |
| --- | --- | --- |
| App shell (HTML/CSS/JS/icons) | **Precache** at install, then **cache-first with background refresh** | Always loads; a fresh copy updates next visit |
| `GET /api/risk-zones` | **Network-first**, cache last body to IndexedDB | Risk changes; prefer live, fall back to last-known |
| `GET /api/hazards` | **Network-first**, cache last body to IndexedDB | Same reasoning as risk zones |
| `GET /api/risk?lat=&lon=` | **Network-first**, cache the last answer to IndexedDB | Regional-grid point lookup; the user's own cell must survive offline |
| Everything else same-origin GET | **Cache-first with background refresh** | Static/semi-static assets |

Why not stale-while-revalidate everywhere? API data drives safety-relevant UI; serving a stale body as if it were live is worse than a short wait, so API routes are network-first and clearly marked when served from cache.

### Cache key correctness

Cache lookups use `caches.match(request)` with `{ ignoreVary: true }`. Reason: the preview server sends `Vary: Origin`, and Vite adds `crossorigin` to some asset tags, so a plain `cache.match` can miss cached JS/CSS and produce offline 503s. Both `ignoreVary` and an explicit `ignoreSearch` fallback are applied for the shell.

---

## IndexedDB / local storage

Database name **`safegrid-offline`**, one object store **`snapshots`** (`keyPath: "key"`). Three snapshots are held:

| key | Contents | Written by |
| --- | --- | --- |
| `risk-zones` | `{ key, geojson, savedAt, isLive }` | `saveRiskZones()` on a successful live response |
| `hazards` | `{ key, payload, savedAt, isLive }` where `payload` is `{ is_live, hazards[] }` | `saveHazards()` on a successful live response |
| `grid-cell` | `{ key, payload, savedAt, isLive }` where `payload` is the point-lookup answer for the user's location | `saveGridCellRisk()` on a successful live response |

All access goes through `frontend/src/offline/storage.js` (browser-free helpers live in `frontend/src/offline/policy.js` and are unit-tested). Snapshots are overwritten on each successful fetch (last-known wins); nothing is appended or merged.

Serving from cache stamps the data:
- `is_live: false` and `cached_at` on the top-level object.
- For hazards **every hazard object** is also stamped `is_live: false` + `cached_at`, so a single marker can be rendered as cached even if the payload is mixed.
- For the grid point lookup (`/api/risk`) the answer object is stamped `is_live: false` + `cached_at`; the stored snapshot is never mutated.

The cache is not mutated in place — stamped copies are returned so the stored snapshot stays pristine.

---

## Regional risk grid storage (the `grid_cells` table)

The standing regional grid (`docs/RISK_MODEL.md` § 4.1) is scored by Person 2 and
served by Person 1; Person 4 owns its storage. **A grid cell is not a hazard event**,
so it does *not* live in `risk_results` (which is keyed by `hazard_id`, and whose
`affected_area` is `NOT NULL`). It gets its own table:

```sql
CREATE TABLE IF NOT EXISTS grid_cells (
    cell_id TEXT PRIMARY KEY,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    cell_size REAL NOT NULL,
    risk_level TEXT NOT NULL,
    severity_score REAL NOT NULL,
    precipitation_mm REAL,
    affected_area TEXT,          -- the cell square, GeoJSON, optional
    computed_at TEXT NOT NULL,   -- when the cell was scored
    generated_at TEXT NOT NULL   -- when the whole run happened
);
```

Repository functions (`backend/app/db/repository.py`): `save_grid_cell`,
`save_grid_snapshot` (one immutable run in a single transaction), `get_grid_cell`,
`list_grid_cells`, `clear_grid_cells`, `is_grid_cell_live`.

**Freshness.** `generated_at` is stored per cell so `is_live` can be derived, never
hardcoded. `is_grid_cell_live(cell, ttl_seconds, now)` returns `True` only when
`generated_at` is within the TTL (`GRID_CELL_TTL_SECONDS = 3 h` default); a missing
or unparseable timestamp is **not** live. The API must expose **both** `is_live` and
`generated_at` — the flag alone can mislead (see Staleness below).

**Endpoint/storage contract (P4 decision, for P1/P2):**
1. `cell_id` is the primary key and the join key everywhere; the frontend's offline
   snapshot is keyed by it.
2. The point lookup is `GET /api/risk?lat=&lon=` and returns
   `risk_level`, `severity_score`, `cell polygon`, `computed_at`, `generated_at`,
   `is_live`. Out-of-region (no cell) must be reported as *outside coverage*, never `LOW`.
3. The grid is refreshed on whatever cadence Person 1 chooses; `is_live` is computed
   from `generated_at` + `GRID_CELL_TTL_SECONDS`, so changing the cadence is a config
   change, not a schema change.
4. No per-cell rows on `hazards` / `risk_results`; a cell never becomes a hazard.

---

## Staleness

`isStale(cachedAt, now, maxAgeMs)` (in `frontend/src/offline/policy.js`) reports whether a cached timestamp is too old.

- **Default threshold:** `STALE_AFTER_MS = 3 hours`.
- **Meaning:** data older than 3 hours is flagged stale in the UI.
- **Justification:** the normal ingestion cadence is 1–3 hours, so data older than one full cycle may not reflect current conditions.
- **Limitation:** during an active hazard the useful window is shorter; the frontend should adopt an adaptive cadence and tighten this threshold (e.g. to the active-hazard interval) when any zone is HIGH. The UI must always show the `cached_at` timestamp regardless, so users are never misled by the flag alone.

---

## UI requirement

The frontend must visually distinguish:

- 🟢 Live data (fetched now, `is_live: true`)
- 🟠 Cached data (last-known, `is_live: false` — show `cached_at`)
- API unavailable (no live data and no cache)

Person 3 renders this (connection badge + per-marker cached label); Person 4 supplies the `is_live` / `cached_at` signals. Fields follow `docs/FRONTEND_CONTRACT.md`.

---

## Synchronization

Out of scope for the MVP. If user-queued actions are added later, they will be queued in IndexedDB and flushed on reconnect with conflict handling.

---

## Testing

- Unit tests (no browser): `frontend/test/policy.test.js`, `frontend/test/storage.test.js` — run with `npm test` from `frontend/`.
- Manual offline check: `npm run build && npm run preview`, load once, then DevTools → Application → Service Workers (activated) → Network → **Offline** → reload.

---

## Change log

| Date | Change | Author |
| --- | --- | --- |
| 2026-10-17 | Added regional-grid storage: `grid_cells` table + repository fns, `is_live` freshness from `generated_at`; `/api/risk` point-lookup offline cache (SW `offline-v5`); documented the grid storage/endpoint contract | Person 4 |
| 2026-10-19 | Contract implemented by Person 1: `GET /api/risk?lat=&lon=` reads `grid_cells` and serves the three agreed states (`outside_coverage` / `no_data` / scored), exposing both `generated_at` and derived `is_live`. Snapshot is now refreshed by `run_grid()` every 120 min, below `GRID_CELL_TTL_SECONDS` (3h) | Person 1 |
| 2026-10-13 | Documented implemented strategy; added `/api/hazards` caching + per-hazard `is_live:false`; added `STALE_AFTER_MS`; added `preview.proxy` | Person 4 |
| 2026-10-11 | Initial placeholder | Person 4 |
