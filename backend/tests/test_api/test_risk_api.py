"""
Tests for GET /api/risk?lat=&lon= (the point lookup Person 4 specified).

The endpoint reads the shared dev `safegrid.db` by default, so these tests
re-point its `get_grid_cell` call at a private database. That keeps API tests
off the dev database (which holds the real Gokak snapshot) while still
exercising P2's scoring, P4's writer and the endpoint for real.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.api import risk as risk_api
from app.core.config import settings
from app.db import get_grid_cell as _get_grid_cell  # aliased: tests monkeypatch the exported one
from app.db import init_db, save_grid_snapshot
from app.db.session import Database
from app.ingestion.grid_run import (
    region_from_settings,
    spec_from_settings,
    storage_rows,
)
from app.main import app
from app.risk.grid import cell_id_at
from app.risk.rain_grid import CellForecast, HourlySample, score_grid

# Inside the test region below, but no cell is stored there.
INSIDE_POINT = (17.05, 74.05)
# Bangalore: comfortably outside every pilot bbox we configure.
OUTSIDE_POINT = (12.97, 77.59)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def grid_db(tmp_path, monkeypatch):
    """
    A private grid_cells wired into the endpoint's repository call.

    A temp *file* rather than ":memory:": SQLite's in-memory connection is
    bound to the thread that opened it, and TestClient runs route handlers on
    a worker thread.
    """
    database = Database(db_path=tmp_path / "grid_test.db")
    init_db(database=database)
    monkeypatch.setattr(
        risk_api,
        "get_grid_cell",
        lambda cell_id: _get_grid_cell(cell_id, database=database),
    )
    return database


@pytest.fixture
def pilot_region(monkeypatch):
    """
    Pins the region to known coordinates so these tests are independent of a
    developer's local .env — which may point the pilot anywhere at all.
    A bbox with no stored cells, so coverage and no-data stay deterministic.
    """
    monkeypatch.setattr(settings, "grid_region_name", "test-region")
    monkeypatch.setattr(settings, "grid_min_lat", 17.0)
    monkeypatch.setattr(settings, "grid_min_lon", 74.0)
    monkeypatch.setattr(settings, "grid_max_lat", 17.2)
    monkeypatch.setattr(settings, "grid_max_lon", 74.2)
    monkeypatch.setattr(settings, "grid_center_lat", None)
    monkeypatch.setattr(settings, "grid_center_lon", None)


def _score_and_store(latitude, longitude, database, generated_at=None):
    """Scores one cell through the real P2 -> P4 path and stores it."""
    spec = spec_from_settings()
    cell_id = cell_id_at(spec, latitude, longitude)
    snapshot = score_grid(
        spec,
        [
            CellForecast(
                cell_id=cell_id,
                samples=[HourlySample(precipitation_mm=45.0, time="2026-10-19T06:00")],
            )
        ],
        generated_at=generated_at,
    )
    save_grid_snapshot(
        storage_rows(spec, snapshot),
        generated_at=snapshot.generated_at,
        database=database,
    )
    return snapshot


def test_scored_point_returns_exactly_what_the_engine_scored(
    client, grid_db, pilot_region
):
    """End to end: P2 scores, P4 stores, the API reports the same answer."""
    snapshot = _score_and_store(*INSIDE_POINT, grid_db)
    cell_id = cell_id_at(spec_from_settings(), *INSIDE_POINT)

    response = client.get("/api/risk", params={"lat": INSIDE_POINT[0], "lon": INSIDE_POINT[1]})

    assert response.status_code == 200
    body = response.json()
    assert body["in_coverage"] is True
    assert body["reason"] is None
    assert body["cell_id"] == cell_id
    assert body["risk_level"] == snapshot.cells[cell_id].risk_level
    assert body["severity_score"] == snapshot.cells[cell_id].severity_score
    assert body["affected_area"]["type"] == "Polygon"
    assert body["generated_at"] == snapshot.generated_at
    assert body["is_live"] is True


def test_a_stored_cell_is_served_even_outside_the_configured_region(
    client, grid_db, pilot_region
):
    """
    Coverage follows the data, not the config box. Score a place once and a
    single running server can answer for it without being restarted.
    """
    outside_lat, outside_lon = OUTSIDE_POINT
    snapshot = _score_and_store(outside_lat, outside_lon, grid_db)

    body = client.get(
        "/api/risk", params={"lat": outside_lat, "lon": outside_lon}
    ).json()

    assert body["in_coverage"] is True
    assert body["reason"] is None
    assert body["cell_id"] in snapshot.cells
    assert body["risk_level"] == snapshot.cells[body["cell_id"]].risk_level


def test_inside_but_unscored_is_no_data_not_low(client, grid_db, pilot_region):
    """Coverage is a claim about modelling, not about weather: no cell != LOW."""
    response = client.get("/api/risk", params={"lat": INSIDE_POINT[0], "lon": INSIDE_POINT[1]})

    body = response.json()
    assert response.status_code == 200
    assert body["in_coverage"] is True
    assert body["reason"] == "no_data"
    assert body["risk_level"] is None
    assert body["is_live"] is False


def test_outside_the_pilot_region_is_never_reported_as_low(client, grid_db, pilot_region):
    # OUTSIDE_POINT (Bangalore) sits outside the pinned test bbox AND has no
    # stored cell — the only combination that may be refused.
    response = client.get("/api/risk", params={"lat": OUTSIDE_POINT[0], "lon": OUTSIDE_POINT[1]})

    body = response.json()
    assert response.status_code == 200
    assert body["in_coverage"] is False
    assert body["reason"] == "outside_coverage"
    # "we do not model here" must not be served as "it is calm here".
    assert body["risk_level"] is None
    assert body["risk_level"] != "LOW"


def test_is_live_is_derived_from_generated_at_not_hardcoded(
    client, grid_db, pilot_region
):
    """A five-hour-old snapshot is stale against the 3h TTL — but still served."""
    stale = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
    snapshot = _score_and_store(*INSIDE_POINT, grid_db, generated_at=stale)

    body = client.get("/api/risk", params={"lat": INSIDE_POINT[0], "lon": INSIDE_POINT[1]}).json()

    assert body["generated_at"] == stale
    assert body["is_live"] is False
    # Stale is not the same as absent: the last known rating is still readable,
    # which is what Person 3's "cached but stale" warning depends on.
    assert body["risk_level"] == snapshot.cells[body["cell_id"]].risk_level


@pytest.mark.parametrize(
    "params",
    [
        {},  # both missing
        {"lat": 17.05},  # lon missing
        {"lat": 99.0, "lon": 74.05},  # out of range
        {"lat": 17.05, "lon": 200.0},  # out of range
    ],
)
def test_bad_coordinates_are_rejected_not_guessed(client, grid_db, pilot_region, params):
    assert client.get("/api/risk", params=params).status_code == 422
