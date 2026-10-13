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
| Everything else same-origin GET | **Cache-first with background refresh** | Static/semi-static assets |

Why not stale-while-revalidate everywhere? API data drives safety-relevant UI; serving a stale body as if it were live is worse than a short wait, so API routes are network-first and clearly marked when served from cache.

### Cache key correctness

Cache lookups use `caches.match(request)` with `{ ignoreVary: true }`. Reason: the preview server sends `Vary: Origin`, and Vite adds `crossorigin` to some asset tags, so a plain `cache.match` can miss cached JS/CSS and produce offline 503s. Both `ignoreVary` and an explicit `ignoreSearch` fallback are applied for the shell.

---

## IndexedDB / local storage

Database name **`safegrid-offline`**, one object store **`snapshots`** (`keyPath: "key"`). Two snapshots are held:

| key | Contents | Written by |
| --- | --- | --- |
| `risk-zones` | `{ key, geojson, savedAt, isLive }` | `saveRiskZones()` on a successful live response |
| `hazards` | `{ key, payload, savedAt, isLive }` where `payload` is `{ is_live, hazards[] }` | `saveHazards()` on a successful live response |

All access goes through `frontend/src/offline/storage.js` (browser-free helpers live in `frontend/src/offline/policy.js` and are unit-tested). Snapshots are overwritten on each successful fetch (last-known wins); nothing is appended or merged.

Serving from cache stamps the data:
- `is_live: false` and `cached_at` on the top-level object.
- For hazards **every hazard object** is also stamped `is_live: false` + `cached_at`, so a single marker can be rendered as cached even if the payload is mixed.

The cache is not mutated in place — stamped copies are returned so the stored snapshot stays pristine.

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
| 2026-10-13 | Documented implemented strategy; added `/api/hazards` caching + per-hazard `is_live:false`; added `STALE_AFTER_MS`; added `preview.proxy` | Person 4 |
| 2026-10-11 | Initial placeholder | Person 4 |
