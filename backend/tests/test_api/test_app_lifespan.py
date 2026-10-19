"""
Tests for the FastAPI lifespan: app startup must create the tables and start
the grid refresh loop. Without these, a broken lifespan fails silently in
development and only shows up as a map that never updates.
"""

import time

from fastapi.testclient import TestClient

import app.main as main
from app.core.config import settings
from app.ingestion.grid_run import GridRunReport


def _report(written: int) -> GridRunReport:
    return GridRunReport(
        region_name="test",
        cell_size_deg=0.1,
        generated_at="2026-10-19T00:00:00+00:00",
        planned_cells=written,
        fetched_records=0,
        scored_cells=written,
        written_cells=written,
        cells_below_window=0,
    )


def test_app_starts_and_serves_with_the_scheduler_disabled():
    """The default test posture: no network loop, lifespan still must not break."""
    with TestClient(main.app) as client:
        assert client.get("/health").status_code == 200


def test_lifespan_starts_the_refresh_loop_when_enabled(monkeypatch):
    calls: list[bool] = []

    async def fake_run_grid_from_settings():
        calls.append(True)
        return _report(written=16)

    monkeypatch.setattr(main, "run_grid_from_settings", fake_run_grid_from_settings)
    monkeypatch.setattr(settings, "grid_scheduler_enabled", True)

    with TestClient(main.app) as client:
        assert client.get("/health").status_code == 200
        # The loop runs on the app's event loop, which only spins while we
        # make requests — so poll briefly instead of assuming it already ran.
        for _ in range(100):
            if calls:
                break
            time.sleep(0.02)

    assert calls, "the grid refresh loop never ran"


def test_lifespan_initialises_the_database(monkeypatch):
    """
    Nothing else creates the tables. Without this call, a fresh clone fails
    with "no such table" until somebody happens to run a test.
    """
    calls: list[bool] = []

    monkeypatch.setattr(main, "init_db", lambda: calls.append(True))
    monkeypatch.setattr(settings, "grid_scheduler_enabled", False)

    with TestClient(main.app):
        pass

    assert calls, "lifespan did not call init_db() on startup"
