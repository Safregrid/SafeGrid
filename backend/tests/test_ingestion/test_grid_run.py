"""
Tests for the regional grid runner (Person 1's orchestration layer).

No network: FakeClient stands in for OpenMeteo and returns the same shape the
real API produces, so the whole cell_requests -> fetch -> group -> score ->
store chain is exercised for real with an in-memory database.
"""

from datetime import datetime, timedelta

import pytest

from app.core.config import settings
from app.db import init_db, list_grid_cells, list_hazards_with_risk, save_grid_snapshot
from app.db.session import Database
from app.ingestion.grid_run import (
    forecast_days_for,
    group_into_cell_forecasts,
    region_from_settings,
    run_grid,
    spec_from_settings,
    storage_rows,
)
from app.models.data import DataRecord
from app.models.hazard import GeoPoint
from app.risk.grid import GridSpec, Region
from app.risk.rain_grid import CellForecast, HourlySample, cell_requests, score_grid

SPEC = GridSpec(cell_size_deg=0.1)
REGION = Region(name="test-region", min_lat=16.0, min_lon=74.7, max_lat=16.3, max_lon=75.0)


class FakeClient:
    """Duck-typed OpenMeteoClient: returns forecast_days * 24 hours per cell."""

    def __init__(self, precipitation_mm: float = 45.0, omit_amount: bool = False):
        self.precipitation_mm = precipitation_mm
        self.omit_amount = omit_amount
        self.last_forecast_days: int | None = None

    async def fetch_precipitation_many(self, coords, *, forecast_days=None):
        self.last_forecast_days = forecast_days
        records: list[DataRecord] = []

        for cell_id, lat, lon in coords:
            for hour in range((forecast_days or 1) * 24):
                timestamp = datetime(2026, 10, 19) + timedelta(hours=hour)
                amount = None if self.omit_amount else self.precipitation_mm
                records.append(
                    DataRecord(
                        id=f"{cell_id}:{timestamp.isoformat()}",
                        data_type="weather",
                        source="open_meteo",
                        timestamp=timestamp,
                        location=GeoPoint(coordinates=[lon, lat]),
                        magnitude=amount,
                        probability=40.0,
                        specific_data={
                            "precipitation_mm": amount,
                            "wind_speed_kmh": 10.0,
                            "wind_gusts_kmh": 15.0,
                            "weather_code": 61,
                        },
                    )
                )

        return records


def _fresh_db() -> Database:
    database = Database(db_path=":memory:")
    init_db(database=database)
    return database


# --- forecast_days_for -------------------------------------------------------


def test_forecast_days_covers_the_window():
    assert forecast_days_for(24) == 1
    assert forecast_days_for(1) == 1
    assert forecast_days_for(25) == 2
    assert forecast_days_for(48) == 2
    assert forecast_days_for(49) == 3


def test_forecast_days_rejects_a_useless_window():
    with pytest.raises(ValueError, match="window_hours must be positive"):
        forecast_days_for(0)


# --- group_into_cell_forecasts ----------------------------------------------


async def test_grouping_buckets_by_cell_and_keeps_hour_order():
    requests = cell_requests(SPEC, REGION)
    records = await FakeClient().fetch_precipitation_many(requests, forecast_days=1)

    forecasts = group_into_cell_forecasts(records)

    assert len(forecasts) == len(requests)
    assert forecasts[0].cell_id == requests[0][0]
    assert len(forecasts[0].samples) == 24
    # Order must survive: _peak_sample() reads the FIRST window_hours entries.
    assert [sample.time for sample in forecasts[0].samples[:3]] == [
        datetime(2026, 10, 19, 0).isoformat(),
        datetime(2026, 10, 19, 1).isoformat(),
        datetime(2026, 10, 19, 2).isoformat(),
    ]
    assert forecasts[0].samples[5].precipitation_mm == 45.0
    assert forecasts[0].samples[5].precipitation_probability == 40.0


async def test_grouping_skips_hours_with_no_precipitation_value():
    """A null amount cannot be classified — dropped, never read as 0 mm."""
    requests = cell_requests(SPEC, REGION)[:1]
    records = await FakeClient(omit_amount=True).fetch_precipitation_many(
        requests, forecast_days=1
    )

    forecasts = group_into_cell_forecasts(records)

    assert forecasts == []


# --- storage_rows (the P2 -> P4 field adapter) --------------------------------


def test_storage_rows_bridges_polygon_to_affected_area():
    """P2 calls it `polygon`; P4's grid_cells column is `affected_area`."""
    cell_id = cell_requests(SPEC, REGION)[0][0]
    snapshot = score_grid(
        SPEC,
        [
            CellForecast(
                cell_id=cell_id,
                samples=[HourlySample(precipitation_mm=45.0, time="2026-10-19T00:00")],
            )
        ],
    )

    rows = storage_rows(SPEC, snapshot)

    assert len(rows) == 1
    row = rows[0]
    assert row["cell_id"] == cell_id
    assert row["affected_area"] == snapshot.cells[cell_id].polygon
    assert row["cell_size"] == SPEC.cell_size_deg
    assert row["latitude"] is not None
    assert row["longitude"] is not None
    assert row["generated_at"] == snapshot.generated_at
    assert row["risk_level"] in {"HIGH", "MODERATE", "LOW"}


def test_storage_rows_are_accepted_by_p4_writer():
    """The adapter is only correct if save_grid_snapshot() takes it as-is."""
    cell_id = cell_requests(SPEC, REGION)[0][0]
    snapshot = score_grid(
        SPEC,
        [CellForecast(cell_id=cell_id, samples=[HourlySample(precipitation_mm=45.0)])],
    )
    database = _fresh_db()

    written = save_grid_snapshot(
        storage_rows(SPEC, snapshot),
        generated_at=snapshot.generated_at,
        database=database,
    )

    assert written == 1
    stored = list_grid_cells(database=database)
    assert stored[0]["cell_id"] == cell_id
    assert stored[0]["affected_area"] is not None


# --- run_grid (end to end) -----------------------------------------------------


async def test_run_grid_scores_and_stores_every_planned_cell():
    database = _fresh_db()
    client = FakeClient()
    expected = len(cell_requests(SPEC, REGION))

    report = await run_grid(SPEC, REGION, client=client, database=database)

    assert report.planned_cells == expected
    assert report.scored_cells == expected
    assert report.written_cells == expected
    assert report.complete
    assert report.cells_below_window == 0

    stored = list_grid_cells(database=database)
    assert len(stored) == expected
    assert {cell["generated_at"] for cell in stored} == {report.generated_at}


async def test_run_grid_derives_forecast_days_from_the_window():
    database = _fresh_db()
    day_client = FakeClient()
    two_day_client = FakeClient()

    await run_grid(SPEC, REGION, client=day_client, database=database)
    assert day_client.last_forecast_days == forecast_days_for(24)

    await run_grid(
        SPEC, REGION, window_hours=48, client=two_day_client, database=database
    )
    assert two_day_client.last_forecast_days == forecast_days_for(48)


async def test_run_grid_reports_cells_that_returned_too_little_forecast():
    """Calling with too small a forecast_days is visible, not silent."""
    database = _fresh_db()
    client = FakeClient()
    expected = len(cell_requests(SPEC, REGION))

    report = await run_grid(
        SPEC, REGION, window_hours=48, forecast_days=1, client=client, database=database
    )

    assert report.cells_below_window == expected
    # Still stored — partial data is reported rather than dropped.
    assert len(list_grid_cells(database=database)) == expected


async def test_run_grid_never_turns_a_cell_into_a_hazard():
    """
    THE contract: grid cells belong in grid_cells only.

    Feeding cells through pipeline.evaluate_and_store() would map data_type
    "weather" -> hazard_type "rainfall" and write one hazard row per grid
    square, which docs/OFFLINE.md forbids. This test fails if anyone wires the
    runner through the event path.
    """
    database = _fresh_db()

    report = await run_grid(SPEC, REGION, client=FakeClient(), database=database)

    assert report.complete
    assert len(list_grid_cells(database=database)) == report.planned_cells
    assert list_hazards_with_risk(database=database) == []


# --- config-driven region ------------------------------------------------------


def test_region_and_spec_are_read_from_settings_not_hard_coded():
    spec = spec_from_settings()
    region = region_from_settings()

    assert spec.cell_size_deg == settings.grid_cell_size_deg
    assert region.name == settings.grid_region_name
    assert (region.min_lat, region.min_lon, region.max_lat, region.max_lon) == (
        settings.grid_min_lat,
        settings.grid_min_lon,
        settings.grid_max_lat,
        settings.grid_max_lon,
    )
    assert region.min_lat <= region.max_lat
