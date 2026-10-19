"""
Rainfall grid scoring for SafeGrid.

Owner: Person 2 (Risk Engine & Geospatial Processing)
Branch: feature/risk-engine

Turns per-cell weather forecasts into a whole-region risk snapshot, and answers
"what is the risk at this point?" from that snapshot. The grid maths live in
grid.py; the per-cell precipitation classification is reused unchanged from
rain.py. This module adds no new hazard thresholds — it only decides *which*
hour of a cell's forecast to classify (the peak hour over a configurable window)
and packages the result.

Design notes:
- Pure functions only. No network, no database, no scheduling. The caller
  (P1) decides how and when to fetch, and injects the forecasts.
- Scoring the whole region produces one immutable snapshot; serving a single
  user is a lookup into that snapshot.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from app.risk.grid import GridSpec, Region, cell_at, parse_cell_id
from app.risk.rain import PrecipitationInput, calculate_precipitation_risk

# Number of forecast hours from now that participate in peak-hour selection.
DEFAULT_WINDOW_HOURS = 24


@dataclass(frozen=True)
class HourlySample:
    """One hour of weather for a cell (the fields the rain engine consumes)."""

    precipitation_mm: float
    wind_speed_kmh: float = 0.0
    wind_gusts_kmh: float = 0.0
    weather_code: int | None = None
    precipitation_probability: float = 100.0
    time: str | None = None


@dataclass(frozen=True)
class CellForecast:
    """All hourly samples available for one grid cell."""

    cell_id: str
    samples: list[HourlySample]


@dataclass(frozen=True)
class CellRisk:
    """Scored result for a single cell. `severity_score` is stored so the API
    layer can pass it on; consumers choose whether to display it."""

    cell_id: str
    risk_level: str
    severity_score: float
    precipitation_mm: float
    polygon: dict[str, Any]
    computed_at: str


@dataclass(frozen=True)
class GridSnapshot:
    """An immutable, point-in-time scoring of a region."""

    spec_label: str
    window_hours: int
    generated_at: str
    cells: dict[str, CellRisk]


@dataclass(frozen=True)
class PointRisk:
    """The user-facing answer for a point.

    Carries level + severity_score + cell polygon + computed_at. `in_coverage`
    is False when the point is outside the scored region — that is NOT the same
    as LOW risk.
    """

    in_coverage: bool
    risk_level: str | None
    severity_score: float | None
    affected_area: dict[str, Any] | None
    computed_at: str | None
    cell_id: str | None = None
    reason: str | None = None


def cell_requests(spec: GridSpec, region: Region) -> list[tuple[str, float, float]]:
    """
    Plans a grid run: one (cell_id, latitude, longitude) per cell in the region.
    The caller fetches weather for these coordinates (in any batching/cadence
    it likes) and passes the result back to score_grid().
    """
    from app.risk.grid import iter_cells

    return [
        (cell.cell_id, cell.center[0], cell.center[1])
        for cell in iter_cells(spec, region)
    ]


def _peak_sample(samples: Iterable[HourlySample], window_hours: int) -> HourlySample | None:
    """The sample with the highest precipitation within the first N hours."""
    window = list(samples)[:window_hours]
    if not window:
        return None
    return max(window, key=lambda sample: sample.precipitation_mm)


def score_grid(
    spec: GridSpec,
    forecasts: Iterable[CellForecast],
    *,
    window_hours: int = DEFAULT_WINDOW_HOURS,
    generated_at: str | None = None,
) -> GridSnapshot:
    """
    Scores every provided cell at its peak hour and returns a snapshot.

    Cells with no samples are omitted (no data — not LOW). Cells whose cell_id
    does not belong to `spec` raise ValueError (fail loudly on a mismatched run).
    """
    stamp = generated_at or datetime.now(timezone.utc).isoformat()
    scored: dict[str, CellRisk] = {}

    for forecast in forecasts:
        cell = parse_cell_id(spec, forecast.cell_id)
        peak = _peak_sample(forecast.samples, window_hours)
        if peak is None:
            continue

        latitude, longitude = cell.center
        result = calculate_precipitation_risk(
            PrecipitationInput(
                latitude=latitude,
                longitude=longitude,
                time=peak.time or stamp,
                precipitation_mm=peak.precipitation_mm,
                time_window_hours=1,
                wind_speed_kmh=peak.wind_speed_kmh,
                wind_gusts_kmh=peak.wind_gusts_kmh,
                weather_code=peak.weather_code,
                precipitation_probability=peak.precipitation_probability,
            )
        )

        scored[forecast.cell_id] = CellRisk(
            cell_id=forecast.cell_id,
            risk_level=result.risk_level,
            severity_score=result.severity_score,
            precipitation_mm=peak.precipitation_mm,
            polygon=cell.polygon(),
            computed_at=stamp,
        )

    return GridSnapshot(
        spec_label=spec.label,
        window_hours=window_hours,
        generated_at=stamp,
        cells=scored,
    )


def risk_at_point(
    spec: GridSpec,
    region: Region,
    snapshot: GridSnapshot,
    latitude: float,
    longitude: float,
) -> PointRisk:
    """
    Looks up the risk for a point in a snapshot.

    - Outside the region  -> in_coverage=False (never reported as LOW).
    - Inside, no scored cell -> in_coverage=True with risk_level=None ("no_data").
    - Otherwise the cell's level + severity_score + polygon + computed_at.
    """
    if not region.contains(latitude, longitude):
        return PointRisk(
            in_coverage=False,
            risk_level=None,
            severity_score=None,
            affected_area=None,
            computed_at=None,
            reason="outside_coverage",
        )

    cell = cell_at(spec, latitude, longitude)
    scored = snapshot.cells.get(cell.cell_id)
    if scored is None:
        return PointRisk(
            in_coverage=True,
            risk_level=None,
            severity_score=None,
            affected_area=None,
            computed_at=None,
            cell_id=cell.cell_id,
            reason="no_data",
        )

    return PointRisk(
        in_coverage=True,
        risk_level=scored.risk_level,
        severity_score=scored.severity_score,
        affected_area=scored.polygon,
        computed_at=scored.computed_at,
        cell_id=cell.cell_id,
    )
