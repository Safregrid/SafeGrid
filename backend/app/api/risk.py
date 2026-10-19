"""
GET /api/risk?lat=&lon=: point lookup into the standing regional grid.

Person 1 implements and owns this module. The response contract is Person 4's
(docs/OFFLINE.md, "Endpoint/storage contract"); Person 3 renders it.

Answers "what is the risk at my location?" by reading the stored `grid_cells`
snapshot — not by recomputing. It serves what the last run actually scored, so
what the map shows and what the database holds cannot drift apart.

Exactly three states, and they are never conflated:

    outside the pilot region  -> in_coverage=False, reason="outside_coverage"
    inside, no scored cell    -> in_coverage=True,  reason="no_data"
    inside, cell scored       -> risk_level + severity + geometry + is_live

"Outside coverage" must never be reported as LOW: "we do not model here" and
"we model it and it is calm" are different claims, and only the second one is
evidence. See docs/RISK_MODEL.md § 4.1 and the project rule LOW != safe.

Freshness is derived, never hardcoded: `is_live` comes from P4's
`is_grid_cell_live()` reading `generated_at` against GRID_CELL_TTL_SECONDS.
Both `generated_at` and `is_live` are exposed, as the contract requires.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.db import (
    GRID_CELL_TTL_SECONDS,
    get_grid_cell,
    is_grid_cell_live,
)
from app.ingestion.grid_run import region_from_settings, spec_from_settings
from app.risk.grid import cell_id_at

router = APIRouter(prefix="/risk", tags=["risk"])


def _not_scored(in_coverage: bool, reason: str) -> dict:
    """A response with no risk claim: no level, no geometry, not live."""
    return {
        "in_coverage": in_coverage,
        "reason": reason,
        "cell_id": None,
        "risk_level": None,
        "severity_score": None,
        "affected_area": None,
        "precipitation_mm": None,
        "computed_at": None,
        "generated_at": None,
        "is_live": False,
    }


@router.get("")
def read_risk_at_point(
    latitude: float = Query(..., alias="lat", ge=-90, le=90),
    longitude: float = Query(..., alias="lon", ge=-180, le=180),
) -> dict:
    """
    Risk for one coordinate, from the latest stored grid snapshot.

    Both `lat` and `lon` are required; out-of-range values return 422 rather
    than a guess. Returns 200 for all three states above — being outside the
    pilot region is an expected condition for a small pilot, not an error, so
    the caller reads `reason` instead of handling an exception.
    """
    # Built per request (not at import) so the endpoint and the runner always
    # share one definition of the pilot region via grid_run's helpers. If they
    # ever disagreed, a cell could be scored yet reported as outside coverage.
    spec = spec_from_settings()
    region = region_from_settings()

    if not region.contains(latitude, longitude):
        return _not_scored(in_coverage=False, reason="outside_coverage")

    cell = get_grid_cell(cell_id_at(spec, latitude, longitude))
    if cell is None:
        return _not_scored(in_coverage=True, reason="no_data")

    return {
        "in_coverage": True,
        "reason": None,
        "cell_id": cell["cell_id"],
        "risk_level": cell["risk_level"],
        "severity_score": cell["severity_score"],
        "affected_area": cell["affected_area"],
        "precipitation_mm": cell.get("precipitation_mm"),
        "computed_at": cell["computed_at"],
        "generated_at": cell["generated_at"],
        "is_live": is_grid_cell_live(cell, ttl_seconds=GRID_CELL_TTL_SECONDS),
    }
