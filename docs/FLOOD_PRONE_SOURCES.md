# Flood-prone source map (for Karnataka pilot)

You're not a dumbass — it's a lot of moving parts, and you're asking the right questions.

## What we need in plain words

We just need:
- A **list of villages** that flood (official, citable) — to pick a specific community.
- A **map outline (shape)** of the flood-prone area around the village — to tell the grid (P2) where to compute risk.

## Verified sources (Belagavi / Bagalkot + Ghataprabha / Malaprabha)

### Tier 1 — Official village list (BEST for picking your village)
- **KSDMA "Action Plan for Flood Risk Management 2021" (Karnataka State Disaster Management Authority)**
  - URL: https://ksdma.karnataka.gov.in/storage/pdf-files/ActionplanforFloodriskmanagement2021.pdf
  - **Gold:** Lists 1,728 flood-vulnerable villages in Karnataka, with tables by sub-basin (Ghataprabha K3, Malaprabha K4, Krishna etc.)
  - **Extracted for you:** `docs/ghataprabha_k3_flood_villages.csv` (466 villages — includes Belagavi/Bagalkot side; has Gokak (CMC/Rural), Mudhol, Jamakhandi, etc.)

### Tier 2 — The actual map shapes (outline to draw on the map)
- **JRC Global River Flood Hazard Maps (Copernicus EMS)** — ~100m, free
  - Data page: https://data.jrc.ec.europa.eu/dataset/jrc-floods-floodmapgl_rp50y-tif
  - FAO catalog (direct GCS/links): http://data.fao.org/catalog/iso/7634ef15-b3d1-44e8-8580-91ba6a71469c
  - License: **CC-BY-4.0** (use, cite, credit) — perfect for college
  - Tip: download the relevant GeoTIFF and **clip** to a box around the chosen village. Export as GeoJSON.
- **Bhuvan (ISRO/NRSC) — Flood Hazard / Flood Annual Layers (WMS)**
  - Thematic WMS: https://bhuvan-vec2.nrsc.gov.in/bhuvan/wms (add in QGIS/MapLibre)
  - Disaster services: https://bhuvan-app1.nrsc.gov.in/disaster/disaster.php
  - Indian govt (attribution required). Great for cross-checking.
- **Karnataka Water Resources Dept (MAPS)** — river/basin + gauge stations
  - https://waterresources.karnataka.gov.in/new-page/MAPS/en
- **data.gov.in — Hydrological/River boundaries (shapefiles, open)** — https://www.data.gov.in/catalog/hydrological-boundaries

### Tier 3 — Validation/ground truth
- **KSNDMC (Karnataka)** — rain gauges, maps, alerts
  - https://www.ksndmc.org/en
- **CWC (Central Water Commission)** — river gauge levels
  - https://cwc.gov.in/

## How this fits (plain explanation)
1. **Pick a village** (e.g. from the CSV) — that's your "specific community". 
2. **Get its flood outline** (JRC or Bhuvan) — draw its flood-prone boundary.
3. **P2** cuts that area into small squares (the grid) and computes risk per square.
4. **P3** draws those squares as red/yellow/green on the map.
5. **P4** stores it so it works offline.

## Who does what
- **P1 (you)** — pick village, get/save the flood-prone outline (GeoJSON), document sources. (Done the village shortlist for Ghataprabha K3: see CSV.)
- **P2 (risk)** — grid + risk calculation.
- **P3 (frontend)** — rendering.
- **P4 (offline/db)** — storage/offline.

## Quick next step (doable in 5 minutes)
1. Open `docs/ghataprabha_k3_flood_villages.csv` and pick **3–5** candidates (look for ones near major rivers/dams in Gokak/Mudhol/Jamakhandi area, e.g. Gokak (CMC), Adibatti, Melavanki, Akkimaradi etc.)
2. Tell me **which one(s)** you prefer — I'll help you clip the JRC/Bhuvan flood outline for it and save it as a GeoJSON in `docs/`.
