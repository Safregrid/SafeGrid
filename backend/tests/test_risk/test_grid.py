"""
Unit tests for the regular lat/lon grid toolkit (backend/app/risk/grid.py).

Owner: Person 2. Pure math — no network, no database, no pipeline.
"""

from __future__ import annotations

import pytest

from app.risk.grid import (
    GridSpec,
    Region,
    cell_at,
    cell_id_at,
    cells_multipolygon,
    iter_cells,
    parse_cell_id,
)

SPEC = GridSpec(cell_size_deg=0.1)
KARNATAKA_LIKE = Region(
    name="test-region",
    min_lat=12.0,
    min_lon=77.0,
    max_lat=12.2,
    max_lon=77.2,
)


def test_cell_id_is_deterministic():
    assert cell_id_at(SPEC, 12.9716, 77.5946) == cell_id_at(SPEC, 12.9716, 77.5946)


def test_point_lies_inside_its_own_cell():
    cell = cell_at(SPEC, 12.9716, 77.5946)
    min_lat, min_lon, max_lat, max_lon = cell.bounds
    assert min_lat <= 12.9716 < max_lat
    assert min_lon <= 77.5946 < max_lon


def test_cell_center_is_inside_the_cell():
    cell = cell_at(SPEC, 12.9716, 77.5946)
    lat, lon = cell.center
    assert cell_id_at(SPEC, lat, lon) == cell.cell_id


def test_adjacent_points_fall_in_different_cells():
    left = cell_at(SPEC, 12.25, 77.29)
    right = cell_at(SPEC, 12.25, 77.31)
    assert (left.row, left.col) != (right.row, right.col)


def test_point_on_boundary_belongs_to_upper_cell():
    cell = cell_at(SPEC, 12.1, 77.0)
    min_lat, _, _, _ = cell.bounds
    assert min_lat == pytest.approx(12.1)


def test_float_boundary_regression():
    """12.3 / 0.1 is 1022.9999999999999 in binary float; must not fall one cell low."""
    cell = cell_at(SPEC, 12.3, 77.3)
    min_lat, min_lon, _, _ = cell.bounds
    assert min_lat == pytest.approx(12.3)
    assert min_lon == pytest.approx(77.3)


def test_cell_id_round_trips():
    cell = cell_at(SPEC, 12.9716, 77.5946)
    assert parse_cell_id(SPEC, cell.cell_id) == cell


def test_parse_rejects_wrong_cell_size():
    cell_id = cell_id_at(SPEC, 12.9716, 77.5946)
    with pytest.raises(ValueError):
        parse_cell_id(GridSpec(cell_size_deg=0.25), cell_id)


def test_parse_rejects_malformed_id():
    with pytest.raises(ValueError):
        parse_cell_id(SPEC, "not-a-cell")


def test_region_contains_edges_and_rejects_outside():
    assert KARNATAKA_LIKE.contains(12.0, 77.0)
    assert KARNATAKA_LIKE.contains(12.2, 77.2)
    assert not KARNATAKA_LIKE.contains(11.9999, 77.0)
    assert not KARNATAKA_LIKE.contains(12.0, 77.2001)


def test_iter_cells_covers_expected_block():
    cells = list(iter_cells(SPEC, KARNATAKA_LIKE))
    rows = {cell.row for cell in cells}
    cols = {cell.col for cell in cells}
    assert len(cells) == len(rows) * len(cols) == 9


def test_cell_polygon_is_closed_ring_in_lon_lat_order():
    polygon = cell_at(SPEC, 12.9716, 77.5946).polygon()
    ring = polygon["coordinates"][0]
    assert polygon["type"] == "Polygon"
    assert ring[0] == ring[-1]
    assert len(ring) == 5
    min_lat, min_lon, max_lat, max_lon = cell_at(SPEC, 12.9716, 77.5946).bounds
    lons = [pt[0] for pt in ring]
    lats = [pt[1] for pt in ring]
    assert min(lons) == pytest.approx(min_lon)
    assert max(lons) == pytest.approx(max_lon)
    assert min(lats) == pytest.approx(min_lat)
    assert max(lats) == pytest.approx(max_lat)


def test_cells_multipolygon_has_one_polygon_per_cell():
    cells = list(iter_cells(SPEC, KARNATAKA_LIKE))
    multi = cells_multipolygon(iter(cells))
    assert multi["type"] == "MultiPolygon"
    assert len(multi["coordinates"]) == len(cells)


def test_invalid_spec_and_region_are_rejected():
    with pytest.raises(ValueError):
        GridSpec(cell_size_deg=0)
    with pytest.raises(ValueError):
        Region(name="bad", min_lat=13.0, min_lon=77.0, max_lat=12.0, max_lon=78.0)
    with pytest.raises(ValueError):
        cell_at(SPEC, 91.0, 77.0)
