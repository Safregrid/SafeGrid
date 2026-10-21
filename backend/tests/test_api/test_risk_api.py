"""
Tests for GET /api/risk?lat=&lon= (the point lookup Person 4 specified).

The endpoint reads the shared dev `safegrid.db` by default, so these tests
re-point its `get_grid_cell` call at a private database. That keeps API tests
off the dev database (which holds the real Gokak snapshot) while still
exercising P2's scoring, P4's writer and the endpoint for real.
"""

from datetime import datetime, timedelta, timezone

import asyncio

import httpx
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


# --- on-demand scoring ---------------------------------------------------------


def test_an_unscored_point_is_scored_then_remembered(
    client, grid_db, pilot_region, monkeypatch
):
    """Nobody has asked about this square before: score it, store it, answer."""
    monkeypatch.setattr(settings, "grid_score_on_demand", True)
    calls: list[tuple[float, float]] = []

    async def fake_score(spec, latitude, longitude):
        calls.append((latitude, longitude))
        _score_and_store(latitude, longitude, grid_db)
        return _get_grid_cell(cell_id_at(spec, latitude, longitude), database=grid_db)

    monkeypatch.setattr(risk_api, "score_cell_on_demand", fake_score)

    first = client.get(
        "/api/risk", params={"lat": INSIDE_POINT[0], "lon": INSIDE_POINT[1]}
    ).json()
    second = client.get(
        "/api/risk", params={"lat": INSIDE_POINT[0], "lon": INSIDE_POINT[1]}
    ).json()

    assert calls == [INSIDE_POINT]
    assert first["in_coverage"] is True
    assert first["reason"] is None
    assert first["risk_level"] is not None
    # The second ask is served from storage and costs no weather request.
    assert second["cell_id"] == first["cell_id"]
    assert len(calls) == 1


def test_on_demand_is_off_by_default_in_tests(client, grid_db, pilot_region):
    """
    conftest disables it so a test session can never reach the network by
    accident; the no-data answer is therefore the unstubbed behaviour.
    """
    body = client.get(
        "/api/risk", params={"lat": INSIDE_POINT[0], "lon": INSIDE_POINT[1]}
    ).json()

    assert body["reason"] == "no_data"


def test_on_demand_failure_degrades_to_no_data_not_a_500(
    client, grid_db, pilot_region, monkeypatch
):
    """A weather API outage must not turn a lookup into a server error."""
    monkeypatch.setattr(settings, "grid_score_on_demand", True)

    async def boom(spec, latitude, longitude):
        raise RuntimeError("weather API down")

    monkeypatch.setattr(risk_api, "score_cell_on_demand", boom)

    response = client.get(
        "/api/risk", params={"lat": INSIDE_POINT[0], "lon": INSIDE_POINT[1]}
    )

    assert response.status_code == 200
    assert response.json()["reason"] == "no_data"


# --- stale cells are re-measured, not served as if they were current ----------


def test_a_stale_cell_is_rescored_and_the_fresh_answer_is_served(
    client, grid_db, pilot_region, monkeypatch
):
    """
    A square whose rating has aged past the TTL must be measured again.

    Serving it unchanged would claim "this is calm now" on the strength of a
    three-hour-old measurement - the same error as calling an unscored square
    LOW, only slower.
    """
    monkeypatch.setattr(settings, "grid_score_on_demand", True)
    stale = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
    _score_and_store(*INSIDE_POINT, grid_db, generated_at=stale)

    calls: list[tuple[float, float]] = []

    async def fake_score(spec, latitude, longitude):
        calls.append((latitude, longitude))
        _score_and_store(latitude, longitude, grid_db)
        return _get_grid_cell(cell_id_at(spec, latitude, longitude), database=grid_db)

    monkeypatch.setattr(risk_api, "score_cell_on_demand", fake_score)

    body = client.get(
        "/api/risk", params={"lat": INSIDE_POINT[0], "lon": INSIDE_POINT[1]}
    ).json()

    assert calls == [INSIDE_POINT]
    assert body["reason"] is None
    assert body["is_live"] is True
    assert body["generated_at"] != stale


def test_a_failed_refresh_keeps_the_stale_rating_rather_than_no_data(
    client, grid_db, pilot_region, monkeypatch
):
    """
    A provider outage must not throw away the last rating we hold.

    "No data" is the honest answer when we have nothing. It is a worse answer
    than the truth when we hold a real earlier measurement, so a failed
    refresh falls back to the stale cell and lets the client see `is_live:
    false` rather than losing the rating entirely.
    """
    monkeypatch.setattr(settings, "grid_score_on_demand", True)
    stale = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
    snapshot = _score_and_store(*INSIDE_POINT, grid_db, generated_at=stale)

    calls: list[tuple[float, float]] = []

    async def boom(spec, latitude, longitude):
        calls.append((latitude, longitude))
        raise RuntimeError("weather API down")

    monkeypatch.setattr(risk_api, "score_cell_on_demand", boom)

    body = client.get(
        "/api/risk", params={"lat": INSIDE_POINT[0], "lon": INSIDE_POINT[1]}
    ).json()

    # The stale square was re-measured...
    assert calls == [INSIDE_POINT]
    # ...the re-measure failed, and the earlier rating survived it.
    assert body["in_coverage"] is True
    assert body["reason"] is None
    assert body["is_live"] is False
    assert body["generated_at"] == stale
    assert body["risk_level"] == snapshot.cells[body["cell_id"]].risk_level


async def test_simultaneous_questions_about_one_square_cause_one_fetch(
    grid_db, pilot_region, monkeypatch
):
    """
    A burst of questions must not turn one square into many weather requests.

    Five requests arrive together. The first scores and stores the square; the
    others wait for it and read the stored result, so the provider is asked
    once and every caller gets the same answer.
    """
    monkeypatch.setattr(settings, "grid_score_on_demand", True)
    calls: list[tuple[float, float]] = []

    async def slow_score(spec, latitude, longitude):
        calls.append((latitude, longitude))
        await asyncio.sleep(0.05)  # the window a real provider call occupies
        _score_and_store(latitude, longitude, grid_db)
        return _get_grid_cell(cell_id_at(spec, latitude, longitude), database=grid_db)

    monkeypatch.setattr(risk_api, "score_cell_on_demand", slow_score)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        responses = await asyncio.gather(
            *(
                http.get(
                    "/api/risk",
                    params={"lat": INSIDE_POINT[0], "lon": INSIDE_POINT[1]},
                )
                for _ in range(5)
            )
        )

    bodies = [response.json() for response in responses]

    assert len(calls) == 1
    assert all(body["reason"] is None for body in bodies)
    assert all(body["is_live"] is True for body in bodies)
    assert len({body["cell_id"] for body in bodies}) == 1

