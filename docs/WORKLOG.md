# SafeGrid — Work Log

> **Purpose:** a running, append-only record of what the team built and **why**, kept primarily for the academic report. Git history records *what* changed; this log records the reasoning, decisions and blockers behind it.
>
> **Convention**
> - Newest entry goes on **top** (directly below this header) so appends never conflict.
> - One block per working day, using the template below.
> - Log **decisions and rationale**, not a restatement of commits — link commit hashes instead.
> - Commit the entry as part of the PR that did the work; don't leave it as a separate chore.
> - Per-subsystem detail (e.g. `backend/app/risk/session_log.md`) stays in that subsystem; this file is the **cross-team** summary.
>
> **Backfill note:** this log starts 2026-10-13. Earlier work is recorded in git history and Person 2's `backend/app/risk/session_log.md`.

### Entry template

```
### YYYY-MM-DD — <short title>
**Participants:**
**Shipped:**
**Decisions:**
**Blockers / open:**
**Next:**
```

---

### 2026-10-14 — Merge Person 2's risk engine; vertical slice live

**Participants:** P1 (Rajat)

**Shipped:**
- Merged `feature/risk-engine` into `feature/data-ingestion` (`264fb53`), bringing in the classifier type-mapping, the IMD rainfall engine (`rain.py`), and the `pipeline.py` seam.
- Resolved two conflicts:
  - `backend/app/risk/pipeline.py` — took Person 2's seam (returns `RiskResult`; adds `evaluate_all` / `evaluate_and_store_all`). The seam lives in Person 2's subsystem.
  - `docs/RISK_MODEL.md` — kept the v2 framework as the backbone and folded in Person 2's IMD rainfall thresholds; added a merge-resolution change-log row.
- Adjusted the `/api/risk-zones` tests to the shared dev database (attribute access for the model return; find-seeded-hazard-by-id instead of asserting an exact count; collection-shape check in place of a strict "empty" assertion).
- Full backend suite green: **18 passed** (run from `backend/`).

**Decisions:**
- `pipeline.py` is the single engine entry point; the API is a read-only view over persisted `RiskResult` rows.
- Rainfall threshold table standardised on **IMD** spell-rate (canonical), superseding the earlier WMO hourly table.
- The **data-derived grid footprint** supersedes the v1 `radius = f(score)` rule (v1 survives only as a labelled fallback).
- Logging strategy: no freeform `log.txt`. Keep git history + the docs change-log tables + per-subsystem `session_log.md`, and add this `docs/WORKLOG.md` for the academic narrative.

**Blockers / open:**
- P4: add `r.calculated_at` to `list_hazards_with_risk()`'s JOIN — the column exists (`risk_results.calculated_at NOT NULL`) and is already written, so it is a one-line SELECT change; without it `/api/risk-zones` returns `calculated_at: null` despite it being a documented, required feature property.
- P2: earthquake engine; `seismic → earthquake` fails loudly until then.
- P1: wire the ingestion trigger (call `evaluate_and_store()` after `save_data_record()`, guarded).

**Next:**
- Open the PR for `feature/data-ingestion`; then `feature/risk-engine → main`.
- Wire the ingestion → risk trigger.

---

### 2026-10-13 — `GET /api/risk-zones` vertical slice

**Participants:** P1 (Rajat), with the risk engine authored by P2 (reviewed)

**Shipped:**
- `ea27b8c` — `pipeline.py` seam (`evaluate` / `evaluate_and_store`) connecting ingestion → classification → persistence. *(Superseded by Person 2's version in the 2026-10-14 merge.)*
- `dc525cb` — `GET /api/risk-zones` serving persisted risks as a GeoJSON `FeatureCollection`: router, registration in `main.py` under `/api`, and integration tests; `docs/RISK_MODEL.md`, `docs/API.md` and `docs/ARCHITECTURE.md` updated with change-log rows.
- Fixed `_ZONE_TYPES` typo (`"Ploygon"` → `"Polygon"`), which had silently dropped every zone from the response.

**Decisions:**
- The engine runs **at ingestion**, not per request: ingest → `evaluate_and_store(record)` → persist `Hazard` + `RiskResult`; the API only reads.
- Risk framework **v2** (`severity = hazard_index × exposure_index × vulnerability_index`, plus confidence) is the authoritative model.
- The slice answers Blocker 2 without the earthquake engine — rain works end to end; seismic fails loudly (by design).

**Diagnosed:**
- Four async test failures were a working-directory issue (tests must run from `backend/`), **not** a missing plugin.
- Two `NotImplementedError` failures traced to the stub classifier lacking the `weather → rainfall` mapping — closed by the 2026-10-14 merge.

**Next:** merge Person 2's engine (done the following day).
