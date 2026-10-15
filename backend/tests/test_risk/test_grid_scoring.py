"""
Unit tests for rainfall grid scoring (backend/app/risk/rain_grid.py).

Owner: Person 2. Pure — no network, no database, no scheduling.
"""

from __future__ import annotations

import pytest

from app.risk.grid import GridSpec, Region, cell_at
from app.risk.rain_grid import (
    CellForecast,
    HourlySample,
    cell_requests,
    risk_at_point,
    score_grid,
)

SPEC = GridSpec(cell_size_deg=0.1)
REGION = Region(
    name="test-region",
    min_lat=12.0,
    min_lon=77.0,
    max_lat=12.2,
    max_lon=77.2,
)


def _cell_id(lat: float, lon: float) -> str:
    return cell_at(SPEC, lat, lon).cell_id


def test_cell_requests_covers_region_with_centers():
    requests = cell_requests(SPEC, REGION)
    assert len(requests) == 9
    for cell_id, lat, lon in requests:
        assert cell_id == _cell_id(lat, lon)


def test_peak_hour_is_the_wettest_sample():
    cell_id = _cell_id(12.05, 77.05)
    forecast = CellForecast(
        cell_id=cell_id,
        samples=[
            HourlySample(precipitation_mm=2.0),
            HourlySample(precipitation_mm=25.0),
            HourlySample(precipitation_mm=3.0),
        ],
    )
    snapshot = score_grid(SPEC, [forecast], window_hours=24, generated_at="2026-10-15T00:00:00Z")
    cell = snapshot.cells[cell_id]
    assert cell.precipitation_mm == 25.0
    assert cell.risk_level == "HIGH"
    assert snapshot.generated_at == "2026-10-15T00:00:00Z"
    assert snapshot.window_hours == 24
    assert snapshot.spec_label == "0.1"


def test_window_hours_limits_which_samples_count():
    cell_id = _cell_id(12.05, 77.05)
    forecast = CellForecast(
        cell_id=cell_id,
        samples=[HourlySample(precipitation_mm=2.0), HourlySample(precipitation_mm=25.0)],
    )
    near = score_grid(SPEC, [forecast], window_hours=1, generated_at="t")
    far = score_grid(SPEC, [forecast], window_hours=2, generated_at="t")
    assert near.cells[cell_id].risk_level == "LOW"
    assert far.cells[cell_id].risk_level == "HIGH"


def test_cell_without_samples_is_omitted():
    cell_id = _cell_id(12.05, 77.05)
    snapshot = score_grid(SPEC, [CellForecast(cell_id=cell_id, samples=[])], generated_at="t")
    assert cell_id not in snapshot.cells


def test_mismatched_cell_id_fails_loudly():
    other_spec_id = cell_at(GridSpec(0.25), 12.05, 77.05).cell_id
    forecast = CellForecast(cell_id=other_spec_id, samples=[HourlySample(precipitation_mm=25.0)])
    with pytest.raises(ValueError):
        score_grid(SPEC, [forecast], generated_at="t")


def test_snapshot_cell_carries_polygon_and_timestamp():
    cell_id = _cell_id(12.05, 77.05)
    snapshot = score_grid(
        SPEC,
        [CellForecast(cell_id=cell_id, samples=[HourlySample(precipitation_mm=25.0)])],
        generated_at="2026-10-15T00:00:00Z",
    )
    cell = snapshot.cells[cell_id]
    assert cell.polygon["type"] == "Polygon"
    assert cell.computed_at == "2026-10-15T00:00:00Z"


def test_point_lookup_returns_user_facing_fields():
    cell_id = _cell_id(12.05, 77.05)
    snapshot = score_grid(
        SPEC,
        [CellForecast(cell_id=cell_id, samples=[HourlySample(precipitation_mm=25.0)])],
        generated_at="2026-10-15T00:00:00Z",
    )
    point = risk_at_point(SPEC, REGION, snapshot, 12.05, 77.05)
    assert point.in_coverage is True
    assert point.risk_level == "HIGH"
    assert point.severity_score == snapshot.cells[cell_id].severity_score
    assert point.affected_area["type"] == "Polygon"
    assert point.computed_at == "2026-10-15T00:00:00Z"
    assert point.cell_id == cell_id


def test_point_without_data_has_no_severity_score():
    point = risk_at_point(SPEC, REGION, score_grid(SPEC, [], generated_at="t"), 12.05, 77.05)
    assert point.severity_score is None


def test_point_outside_region_is_not_low():
    snapshot = score_grid(SPEC, [], generated_at="t")
    point = risk_at_point(SPEC, REGION, snapshot, 20.0, 77.0)
    assert point.in_coverage is False
    assert point.risk_level is None
    assert point.reason == "outside_coverage"


def test_point_inside_region_without_scored_cell_is_no_data():
    snapshot = score_grid(SPEC, [], generated_at="t")
    point = risk_at_point(SPEC, REGION, snapshot, 12.05, 77.05)
    assert point.in_coverage is True
    assert point.risk_level is None
    assert point.reason == "no_data"
