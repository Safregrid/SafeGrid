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
about a second would not be honesty, it would just be unhelpfulness.

A cell that has aged past the TTL is treated the same way: a three-hour-old
rating is re-scored instead of being served as if it were current. "We last
measured this three hours ago" and "this is calm right now" are different
claims, and only the second one is evidence. Because the result is stored, only
the first question about a square - and then one per TTL window - ever pays
that cost. Disable with `grid_score_on_demand`.

Only one fetch per square runs at a time. Simultaneous questions about the same
square wait for the first one and then read its stored result, so a burst of
traffic cannot turn one square into many weather requests.

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

import asyncio
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

# One in-flight scoring attempt per square.
#
# Without this, several simultaneous first-time questions about the same square
# would each start their own weather fetch, and the provider would be hit N
# times to answer one question. The lock is held only while a fetch is actually
# running; everything else waits and then reads the stored result.
#
# `_in_flight_users` counts the requests currently holding or waiting for each
# lock. When it reaches zero the lock is dropped, so the table stays bounded by
# the traffic in flight rather than growing with every square ever asked about.
_in_flight: dict[str, asyncio.Lock] = {}
_in_flight_users: dict[str, int] = {}


def _lock_for(cell_id: str) -> asyncio.Lock:
    """
    The lock for one square, creating it on first use.

    No `await` happens between reading and writing the dictionary, so two
    requests arriving at the same moment cannot end up with two different locks
    for the same square.
    """
    lock = _in_flight.get(cell_id)
    if lock is None:
        lock = asyncio.Lock()
        _in_flight[cell_id] = lock
    _in_flight_users[cell_id] = _in_flight_users.get(cell_id, 0) + 1
    return lock


def _release_lock(cell_id: str) -> None:
    """Drops one user of a square's lock, and the lock itself if it was the last."""
    _in_flight_users[cell_id] = _in_flight_users.get(cell_id, 0) - 1
    if _in_flight_users[cell_id] <= 0:
        _in_flight_users.pop(cell_id, None)
        _in_flight.pop(cell_id, None)


def _needs_scoring(cell: dict | None) -> bool:
    """
    Whether a square needs (re)scoring: it is missing, or what we hold is old.

    A stale cell is a rating we took three hours ago. Serving it unchanged
    would claim "this is calm now" on the strength of an old measurement, and
    answering `no_data` instead would throw away a real earlier answer. Both
    are wrong, so the cell is re-scored and only the fetch can fail.
    """
    if cell is None:
        return True
    return not is_grid_cell_live(cell, ttl_seconds=GRID_CELL_TTL_SECONDS)


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
    Score one square now: the first time anybody asks about it, or again when
    what we hold has aged out.

    A failure here is logged and reported as "nothing to serve" rather than
    raised: a weather API being down must not turn a lookup into a 500. The
    caller decides what to do about it - a missing square becomes "no data",
    and a square we already hold a rating for keeps that rating, marked stale.
    """
    try:
        return await score_cell_on_demand(spec, latitude, longitude)
    except Exception:
        logger.exception(
            "on-demand scoring failed for (%s, %s)", latitude, longitude
        )
        return None


async def _refresh_cell(
    spec: GridSpec,
    cell_id: str,
    latitude: float,
    longitude: float,
    *,
    stored: dict | None,
) -> dict | None:
    """
    (Re)score the square containing a point, at most one attempt at a time.

    Three rules, in order of importance:

    1. Only one attempt per square runs at a time. A request that arrives
       while a fetch is in flight waits for it, then re-reads the cell - and
       finds it already fresh - instead of starting a second fetch of the
       same square.
    2. The waiters read the *stored* result, so every caller of a burst gets
       the same answer, not two slightly different ones.
    3. A failed refresh never destroys what we already had. If the provider
       is down, the last known rating is still served (with `is_live: false`).
       Answering `no_data` while a real earlier answer is on file would throw
       away the only truth we have.
    """
    lock = _lock_for(cell_id)

    try:
        async with lock:
            # Somebody may have refreshed this square while we waited for the
            # lock.
            current = get_grid_cell(cell_id)
            if not _needs_scoring(current):
                return current

            scored = await _score_now(spec, latitude, longitude)
            if scored is not None:
                return scored

            return current or stored
    finally:
        _release_lock(cell_id)


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
    cell_id = cell_id_at(spec, latitude, longitude)
    cell = get_grid_cell(cell_id)

    if settings.grid_score_on_demand and _needs_scoring(cell):
        # Either nobody has asked about this square before, or what we hold has
        # aged past the TTL. Both are answered the same way: score it now, store
        # it, serve it. A stale cell is re-scored rather than served as if it
        # were current, and a failed re-score falls back to the stale answer
        # rather than to "no data".
        cell = await _refresh_cell(
            spec, cell_id, latitude, longitude, stored=cell
        )

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
