"""
Regional grid runner for SafeGrid.

Person 1 owns this module: Person 2's rain_grid package is deliberately pure
("no network, no database, no scheduling ... the caller (P1) decides how and
when to fetch, and injects the forecasts"). This file is that caller.

One run walks the whole pipeline end to end:

    cell_requests(spec, region)                 P2: plan which cells to score
      -> fetch_precipitation_many(coords)       P1: batch weather fetch
      -> group_into_cell_forecasts(records)     P1: DataRecord -> CellForecast
      -> score_grid(spec, forecasts)            P2: classify each cell's peak hour
      -> save_grid_snapshot(rows, ...)          P4: persist into grid_cells

Deliberately NOT used here: pipeline.evaluate_and_store(). A grid cell is a
standing rating of a place, not a reported hazard event. Routing cells through
that function would call identify_hazard(), which maps data_type "weather" to
hazard_type "rainfall", and produce one hazard row plus one risk_result row per
grid square - exactly what docs/OFFLINE.md forbids ("a cell never becomes a
hazard"). Cells belong in grid_cells only.

Run it manually to refresh the configured region, or to score anywhere on
Earth from a single point (no config file needed):

    cd backend && .venv/bin/python -m app.ingestion.grid_run
    cd backend && .venv/bin/python -m app.ingestion.grid_run --lat 14.6219 --lon 74.8818
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from typing import Iterable

from app.core.config import settings
from app.db import Database, db, save_grid_snapshot
from app.ingestion.open_meteo import OpenMeteoClient, split_grid_record_id
from app.ingestion.region import region_around
from app.models.data import DataRecord
from app.risk.grid import GridSpec, Region, parse_cell_id
from app.risk.rain_grid import (
    DEFAULT_WINDOW_HOURS,
    CellForecast,
    GridSnapshot,
    HourlySample,
    cell_requests,
    score_grid,
)


@dataclass(frozen=True)
class GridRunReport:
    """What one run did. `complete` is False when the region was only partly
    scored — partial data is reported, never quietly stored as if it were whole."""

    region_name: str
    cell_size_deg: float
    generated_at: str
    planned_cells: int
    fetched_records: int
    scored_cells: int
    written_cells: int
    cells_below_window: int

    @property
    def complete(self) -> bool:
        return (
            self.planned_cells > 0
            and self.written_cells == self.planned_cells
            and self.scored_cells == self.planned_cells
        )


def forecast_days_for(window_hours: int) -> int:
    """
    Whole forecast days Open-Meteo must return to cover `window_hours` samples.

    The API only supports whole days of hourly data, so this rounds up. Asking
    for its 7-day default instead would fetch ~7x the records score_grid()
    actually reads (it stops after `window_hours`).
    """
    if window_hours <= 0:
        raise ValueError("window_hours must be positive")
    return max(1, -(-window_hours // 24))  # ceiling division


def group_into_cell_forecasts(
    records: Iterable[DataRecord],
) -> list[CellForecast]:
    """
    Buckets flat grid DataRecords into one CellForecast per cell_id.

    Sample order within a cell is preserved as given. That matters:
    rain_grid._peak_sample() takes the first `window_hours` samples, so records
    arriving out of time order would score a different window than intended.
    `split_grid_record_id()` is what recovers the cell_id from each record.
    """
    grouped: dict[str, list[HourlySample]] = {}

    for record in records:
        cell_id, _ = split_grid_record_id(record.id)
        precipitation = record.specific_data.get("precipitation_mm")
        if precipitation is None:
            # No amount to classify. Drop the hour rather than pretend 0 mm.
            continue

        grouped.setdefault(cell_id, []).append(
            HourlySample(
                precipitation_mm=precipitation,
                wind_speed_kmh=record.specific_data.get("wind_speed_kmh") or 0.0,
                wind_gusts_kmh=record.specific_data.get("wind_gusts_kmh") or 0.0,
                weather_code=record.specific_data.get("weather_code"),
                precipitation_probability=(
                    record.probability if record.probability is not None else 100.0
                ),
                time=record.timestamp.isoformat(),
            )
        )

    return [
        CellForecast(cell_id=cell_id, samples=samples)
        for cell_id, samples in grouped.items()
    ]


def storage_rows(spec: GridSpec, snapshot: GridSnapshot) -> list[dict]:
    """
    Adapts P2's CellRisk objects into the dict shape P4's save_grid_snapshot()
    requires.

    The two subsystems were written independently, so the fields do not match
    line for line:

      - P2's `polygon`  ->  P4's `affected_area` column (same GeoJSON, renamed)
      - P2 does not carry centre/size (they are derivable), P4 stores them
        as NOT NULL columns
      - P2 stamps `computed_at` per cell; P4 also wants the run-wide
        `generated_at`, which is what is_grid_cell_live() reads for freshness
    """
    rows: list[dict] = []

    for risk in snapshot.cells.values():
        cell = parse_cell_id(spec, risk.cell_id)
        latitude, longitude = cell.center

        rows.append(
            {
                "cell_id": risk.cell_id,
                "latitude": latitude,
                "longitude": longitude,
                "cell_size": spec.cell_size_deg,
                "risk_level": risk.risk_level,
                "severity_score": risk.severity_score,
                "precipitation_mm": risk.precipitation_mm,
                "affected_area": risk.polygon,
                "computed_at": risk.computed_at,
                "generated_at": snapshot.generated_at,
            }
        )

    return rows


async def run_grid(
    spec: GridSpec,
    region: Region,
    *,
    window_hours: int = DEFAULT_WINDOW_HOURS,
    forecast_days: int | None = None,
    client: OpenMeteoClient | None = None,
    database: Database = db,
) -> GridRunReport:
    """
    Scores every cell of `region` and stores the result as one snapshot.

    `client` and `database` are injectable so tests can run the real pipeline
    with no network and an in-memory database. `forecast_days` defaults to
    whatever covers `window_hours`; pass it explicitly to override.
    """
    planned = cell_requests(spec, region)

    if forecast_days is None:
        forecast_days = forecast_days_for(window_hours)

    fetcher = client or OpenMeteoClient()
    records = await fetcher.fetch_precipitation_many(
        planned,
        forecast_days=forecast_days,
    )

    forecasts = group_into_cell_forecasts(records)
    snapshot = score_grid(spec, forecasts, window_hours=window_hours)

    written = save_grid_snapshot(
        storage_rows(spec, snapshot),
        generated_at=snapshot.generated_at,
        database=database,
    )

    return GridRunReport(
        region_name=region.name,
        cell_size_deg=spec.cell_size_deg,
        generated_at=snapshot.generated_at,
        planned_cells=len(planned),
        fetched_records=len(records),
        scored_cells=len(snapshot.cells),
        written_cells=written,
        cells_below_window=sum(
            1 for forecast in forecasts if len(forecast.samples) < window_hours
        ),
    )


def spec_from_settings() -> GridSpec:
    """Grid cell size from config — the region must never be hard-coded here."""
    return GridSpec(cell_size_deg=settings.grid_cell_size_deg)


def region_from_settings() -> Region:
    """
    Pilot region from config, so repointing the pilot is an env var.

    Two ways to describe it, and centre + radius is the one that matches how a
    user describes where they live ("I am in Sirsi", not four coordinates):

        grid_center_lat/lon (+ grid_radius_km) -> a radius around a point
        grid_min/max_lat/lon                   -> an explicit bounding box

    The centre wins when both are given.
    """
    if settings.grid_center_lat is not None and settings.grid_center_lon is not None:
        return region_around(
            settings.grid_center_lat,
            settings.grid_center_lon,
            settings.grid_radius_km,
            name=settings.grid_region_name,
        )

    return Region(
        name=settings.grid_region_name,
        min_lat=settings.grid_min_lat,
        min_lon=settings.grid_min_lon,
        max_lat=settings.grid_max_lat,
        max_lon=settings.grid_max_lon,
    )


async def run_grid_from_settings(database: Database = db) -> GridRunReport:
    """Convenience entry point: one run using the configured pilot region."""
    return await run_grid(
        spec_from_settings(),
        region_from_settings(),
        window_hours=settings.grid_window_hours,
        database=database,
    )


def _main(argv: list[str] | None = None) -> None:
    """
    One run, over either the configured pilot region or a point given on the
    command line. The point form is the "I live in <village>" case, and needs
    no config file at all:

        python -m app.ingestion.grid_run
        python -m app.ingestion.grid_run --lat 14.6219 --lon 74.8818
        python -m app.ingestion.grid_run --lat 14.6219 --lon 74.8818 --radius-km 35
    """
    parser = argparse.ArgumentParser(description="Score and store one grid run.")
    parser.add_argument("--lat", type=float, help="centre latitude of the area to score")
    parser.add_argument("--lon", type=float, help="centre longitude of the area to score")
    parser.add_argument(
        "--radius-km",
        type=float,
        default=settings.grid_radius_km,
        help=f"radius around that point, in km (default {settings.grid_radius_km:g})",
    )
    args = parser.parse_args(argv)

    if (args.lat is None) != (args.lon is None):
        parser.error("--lat and --lon must be given together")

    region = (
        region_around(args.lat, args.lon, args.radius_km)
        if args.lat is not None
        else region_from_settings()
    )

    report = asyncio.run(
        run_grid(spec_from_settings(), region, window_hours=settings.grid_window_hours)
    )

    print(f"region        : {report.region_name}")
    print(
        f"bounds        : lat {region.min_lat:.4f}..{region.max_lat:.4f}, "
        f"lon {region.min_lon:.4f}..{region.max_lon:.4f}"
    )
    print(f"cell size     : {report.cell_size_deg} deg")
    print(f"planned cells : {report.planned_cells}")
    print(f"records       : {report.fetched_records}")
    print(f"scored cells  : {report.scored_cells}")
    print(f"stored cells  : {report.written_cells}")
    print(f"generated_at  : {report.generated_at}")
    if report.cells_below_window:
        print(
            f"warning       : {report.cells_below_window} cells returned fewer than "
            f"{settings.grid_window_hours} hours of forecast"
        )

    if not report.complete:
        print("INCOMPLETE: not every planned cell was scored and stored.")
        raise SystemExit(1)


if __name__ == "__main__":
    _main()
