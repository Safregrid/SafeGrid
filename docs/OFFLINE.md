# SafeGrid — Offline Strategy

> Status: **PLACEHOLDER — to be filled in by Person 4.**

---

## What offline means in SafeGrid

A PWA cannot fetch new data from internet APIs while the device has no network connectivity.

Offline mode in SafeGrid means:
> Continued access to previously cached/downloaded information, not live disaster detection without communication.

This must be clearly communicated in the UI.

---

## Offline priorities

When implementing offline support, prioritize in this order:

1. Application shell (HTML, CSS, JS, fonts)
2. Emergency instructions (static content)
3. Emergency contacts (static content)
4. Essential static information
5. Last-known hazard and risk zone GeoJSON
6. Queued user actions (if reporting is implemented)

Do not attempt to make every feature offline-capable in the MVP.

---

## Service Worker strategy

> Person 4 must document the chosen caching strategy here.

Candidate strategies:
- **Cache-first** for static assets (app shell)
- **Network-first with cache fallback** for hazard/risk API data
- **Stale-while-revalidate** for semi-static content

Document the chosen strategy and reason for each resource type.

---

## UI requirement

The frontend must visually distinguish:

- 🟢 Live data (fetched from backend now)
- 🟠 Cached data (last-known, may be stale — show timestamp)

Person 3 (frontend) and Person 4 (offline) must agree on how this signal is communicated.

---

## IndexedDB / local storage

> Scope and schema: NOT YET DECIDED.

Likely candidates for local storage:
- Last-known `risk-zones` GeoJSON
- Emergency contacts list
- User preferences

---

## Synchronization

If user-queued actions are implemented (e.g. local hazard reports):
- Queue locally in IndexedDB
- Sync when connectivity is restored
- Handle conflicts

This is a P1 feature — not required for MVP.
