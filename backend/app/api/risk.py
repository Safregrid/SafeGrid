"""
GET /api/risk?lat=&lon=: point lookup into the standing regional grid.

Person 1 implements and owns this module. The response contract is Person 4's
(docs/OFFLINE.md, "Endpoint/storage contract"); Person 3 renders it.

Answers "what is the risk at my location?" by reading the stored `grid_cells`
snapshot — not by recomputing. It serves what the last run actually scored, so
what the map shows and what the database holds cannot drift apart.

**Stored cells decide coverage, not the configured box.** If a square was ever
scored for this point, it is served — because having scored it is precisely
what "in coverage" means. The configured region only decides what the scheduler
refreshes; it is not a licence to withhold data we already hold. This lets one
running server answer for many places.

Exactly three states, and they are never conflated:

    a scored cell exists          -> risk_level + severity + geometry + is_live
    no cell, inside the region    -> in_coverage=True,  reason="no_data"
    no cell, outside the region   -> in_coverage=False, reason="outside_coverage"

When no cell is stored, the square is scored **on demand** (weather fetched,
scored, stored) and then served. Saying "we do not know" when finding out takes
about a second would not be honesty, it would just be unhelpfulness. Because
the result is stored, only the first question about a square ever pays that
cost. Disable with `grid_score_on_demand`.

"Outside coverage" must never be reported as LOW: "we do not model here" and
"we model it and it is calm" are different claims, and only the second one is
evidence. See docs/RISK_MODEL.md § 4.1 and the project rule LOW != safe.

Note the lookup is by cell_id, which encodes the cell size. Changing
`grid_cell_size_deg` describes a different grid, so previously scored cells
will not be found — they stay in the database but read as no-data.

Freshness is derived, never hardcoded: `is_live` comes from P4's
`is_grid_cell_live()` reading `generated_at` against GRID_CELL_TTL_SECONDS.
Both `generated_at` and `is_live` are exposed, as the contract requires.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query

from app.core.config import settings
from app.db import (
    GRID_CELL_TTL_SECONDS,
    get_grid_cell,
    is_grid_cell_live,
)
from app.ingestion.grid_run import (
    region_from_settings,
    score_cell_on_demand,
    spec_from_settings,
)
from app.risk.grid import GridSpec, cell_id_at

logger = logging.getLogger("safegrid.api.risk")

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


async def _score_now(spec: GridSpec, latitude: float, longitude: float) -> dict | None:
    """
    Score one square the first time anybody asks about it.

    A failure here is logged and reported as "no data" rather than raised: a
    weather API being down must not turn a lookup into a 500, and "we have no
    data" remains the truthful answer either way.
    """
    try:
        return await score_cell_on_demand(spec, latitude, longitude)
    except Exception:
        logger.exception(
            "on-demand scoring failed for (%s, %s)", latitude, longitude
        )
        return None


@router.get("")
async def read_risk_at_point(
    latitude: float = Query(..., alias="lat", ge=-90, le=90),
    longitude: float = Query(..., alias="lon", ge=-180, le=180),
) -> dict:
    """
    Risk for one coordinate, from the stored grid snapshot.

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

    # A stored square outranks the configured box: having scored this square is
    # what "in coverage" means, so we serve it even if the scheduler has since
    # been repointed elsewhere.
    cell = get_grid_cell(cell_id_at(spec, latitude, longitude))

    if cell is None and settings.grid_score_on_demand:
        # Nobody has asked about this square before. Saying "we do not know"
        # when finding out takes about a second would not be honesty, it would
        # just be unhelpfulness. Score it, store it, answer.
        cell = await _score_now(spec, latitude, longitude)

    if cell is not None:
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

    if region.contains(latitude, longitude):
        return _not_scored(in_coverage=True, reason="no_data")

    return _not_scored(in_coverage=False, reason="outside_coverage")
