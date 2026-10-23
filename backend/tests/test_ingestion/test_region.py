"""
Tests for turning a granted location into a grid region (Person 1).

The maths here decides which ground SafeGrid actually looks at, so it is
checked against known distances rather than against itself.
"""

import math

import pytest

from app.core.config import settings
from app.ingestion.grid_run import region_from_settings, spec_from_settings
from app.ingestion.region import KM_PER_DEGREE_LAT, region_around
from app.risk.grid import cell_id_at
from app.risk.rain_grid import cell_requests

SIRSI = (14.6219, 74.8818)  # Uttara Kannada district, Karnataka


def test_the_box_spans_twice_the_radius_in_latitude():
    region = region_around(*SIRSI, radius_km=20.0)

    expected_degrees = 20.0 / KM_PER_DEGREE_LAT
    assert region.max_lat - region.min_lat == pytest.approx(2 * expected_degrees)
    # Symmetric about the granted point.
    assert (region.min_lat + region.max_lat) / 2 == pytest.approx(SIRSI[0])


def test_longitude_degrees_shrink_with_latitude():
    """
    At 60°N a degree of longitude is half a degree of latitude, so the box
    must stretch further east-west to cover the same ground.
    """
    south = region_around(10.0, 75.0, radius_km=20.0)
    north = region_around(60.0, 75.0, radius_km=20.0)

    south_width = south.max_lon - south.min_lon
    north_width = north.max_lon - north.min_lon
    assert north_width == pytest.approx(2 * south_width, rel=0.02)
    # Both still cover 20 km north-south.
    assert north.max_lat - north.min_lat == pytest.approx(south.max_lat - south.min_lat)


def test_sirsi_at_default_radius_lands_where_expected():
    region = region_around(*SIRSI, radius_km=20.0)

    assert region.min_lat == pytest.approx(14.442, abs=0.001)
    assert region.max_lat == pytest.approx(14.802, abs=0.001)
    assert region.min_lon == pytest.approx(74.696, abs=0.001)
    assert region.max_lon == pytest.approx(75.067, abs=0.001)


def test_the_granted_point_always_falls_inside_its_own_region():
    region = region_around(*SIRSI, radius_km=20.0)

    assert region.contains(*SIRSI)
    # ...and the cell it lands in is one the run would actually score.
    spec = spec_from_settings()
    planned = {cell_id for cell_id, _, _ in cell_requests(spec, region)}
    assert cell_id_at(spec, *SIRSI) in planned


def test_a_larger_radius_covers_a_larger_village():
    small = region_around(*SIRSI, radius_km=10.0)
    large = region_around(*SIRSI, radius_km=40.0)

    assert (large.max_lat - large.min_lat) > (small.max_lat - small.min_lat)
    spec = spec_from_settings()
    assert len(cell_requests(spec, large)) > len(cell_requests(spec, small))


def test_a_bigger_village_gets_more_cells_not_finer_ones():
    """
    The cell size never changes with the village: more ground means more
    squares of the same size, because the weather model is what fixes the
    resolution. Claiming finer squares for a small village would be fake
    precision (docs/RISK_MODEL.md § 4.1).
    """
    spec = spec_from_settings()
    big = cell_requests(spec, region_around(*SIRSI, radius_km=40.0))
    small = cell_requests(spec, region_around(*SIRSI, radius_km=10.0))

    assert len(big) > len(small)
    # Every square, in either run, is the same physical size.
    prefix = f"grid:{spec.cell_size_deg}:"
    assert all(cell_id.startswith(prefix) for cell_id, _, _ in big + small)


@pytest.mark.parametrize("radius", [0.0, -5.0])
def test_a_useless_radius_is_refused(radius):
    with pytest.raises(ValueError, match="radius_km must be positive"):
        region_around(*SIRSI, radius_km=radius)


@pytest.mark.parametrize("latitude", [89.0, -89.0, 90.0])
def test_polar_latitudes_are_refused_rather_than_distorted(latitude):
    with pytest.raises(ValueError, match="pole"):
        region_around(latitude, 0.0, radius_km=20.0)


@pytest.mark.parametrize("longitude", [181.0, -181.0])
def test_out_of_range_longitude_is_refused(longitude):
    with pytest.raises(ValueError, match="longitude"):
        region_around(14.0, longitude, radius_km=20.0)


def test_the_region_names_itself_after_the_point():
    region = region_around(*SIRSI, radius_km=20.0)

    assert "14.6219" in region.name
    assert "74.8818" in region.name


def test_a_larger_radius_box_holds_the_smaller_one():
    inner = region_around(*SIRSI, radius_km=10.0)
    outer = region_around(*SIRSI, radius_km=25.0)

    assert outer.contains(inner.min_lat, inner.min_lon)
    assert outer.contains(inner.max_lat, inner.max_lon)


# --- the two ways of describing the configured region -------------------------


def test_config_uses_the_centre_when_one_is_given(monkeypatch):
    monkeypatch.setattr(settings, "grid_center_lat", SIRSI[0])
    monkeypatch.setattr(settings, "grid_center_lon", SIRSI[1])

    region = region_from_settings()

    assert region.contains(*SIRSI)
    assert region.name == settings.grid_region_name


def test_config_falls_back_to_the_bounding_box(monkeypatch):
    monkeypatch.setattr(settings, "grid_center_lat", None)
    monkeypatch.setattr(settings, "grid_center_lon", None)

    region = region_from_settings()

    assert (region.min_lat, region.max_lat) == (
        settings.grid_min_lat,
        settings.grid_max_lat,
    )


def test_math_sanity_one_degree_is_about_111_km():
    """The constant the whole radius scheme rests on."""
    assert KM_PER_DEGREE_LAT == pytest.approx(111.32, abs=0.01)
    assert math.isclose(40075.0 / 360.0, KM_PER_DEGREE_LAT)
