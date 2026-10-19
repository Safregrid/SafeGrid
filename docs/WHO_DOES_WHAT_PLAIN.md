# Who does what? (Plain explanation)

You asked: which is higher priority, village names OR P2's "what P1 should do" list?

**Answer: Village names + data source first.** Then set up the grid/ingestion (P2's list). Why: You can't define the grid region without picking a village/area.

## What P2 is asking from P1 (in simple terms)

P2 said P1 needs to do:
1. **`fetch_precipitation_many(coords)`** — Right now the code fetches weather for 1 location at a time. But a grid has many squares. Open-Meteo can take many coordinates in one go (up to 1000). So P1 needs to add a function to fetch weather for many grid squares in 1 request.
2. **Run the grid on a schedule (not per-record)** — Instead of running risk every time something is ingested (per user/request), we should run risk for the whole grid **every few hours** and cache it. This is the shared grid idea.
3. **Lookup endpoint** — An API so the frontend can ask: "For this lat/lon, what's the risk?" Return just that cell's result. This is small API work (P1 docs the contract).

So these are technical changes in the backend (ingestion/pipeline). P1 = Rajat.

## But first, the village (data)

Before step 2 makes sense, you need to know **which area** to put the grid over. That comes from the flood-prone map + a chosen village.

- You now have: `docs/ghataprabha_k3_flood_villages.csv` (466 villages, official KSDMA). 
- Shortlist: `docs/village_shortlist_belagavi_bagalkot.txt`.
- Flood-prone sources: `docs/FLOOD_PRONE_SOURCES.md`.

**Recommended pick (safe, well-documented):** **Gokak (CMC)** — Very High risk, floods repeatedly (news 2021/2022), near Ghataprabha river. Fits rainfall-driven engine.

## Priority order

**Priority 1 — Get village + flood outline (10–15 min)** → lock the pilot region. Can't set grid without this.

**Priority 2 — Grid/scheduler/endpoint (P1 backend tasks)** → do after locking region (these depend on region).

## Who does what

| Job | Who |
|---|---|
| Pick village + get flood-prone area outline (GeoJSON) | **P1 (you)** |
| Write sources doc/notes | **P1 (you)** |
| Build grid over that area + run risk per cell + schedule | **P2** |
| Add `fetch_precipitation_many()`, trigger/scheduler, lookup endpoint | **P1 (you)** |
| Draw on map | **P3** |
| Store/cache/offline | **P4** |

**Bottom line:** Do Priority 1 first (village + outline). Then do P2's three backend items. I'll help you get the flood outline for Gokak (CMC) as GeoJSON next.