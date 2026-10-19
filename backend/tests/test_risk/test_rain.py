"""
Unit tests for the precipitation risk engine (backend/app/risk/rain.py).

Owner: Person 2. These are the engine tests the 2026-10-13 backlog (#1) flagged
as missing. Pure — no network, no database.
"""

from __future__ import annotations

import pytest

from app.risk.grid import GridSpec, cell_at
from app.risk.rain import (
    DEFAULT_GRID_SPEC,
    PrecipitationInput,
    calculate_precipitation_risk,
    process_precipitation_hazard,
)

LAT = 12.9716
LON = 77.5946


def _hazard(
    precip_mm: float,
    *,
    lat: float = LAT,
    lon: float = LON,
    window: int = 1,
    wind_speed: float = 0.0,
    wind_gust: float = 0.0,
    code: int | None = None,
    hazard_id: str = "open-meteo:test",
) -> dict:
    return {
        "id": hazard_id,
        "source": "open_meteo",
        "latitude": lat,
        "longitude": lon,
        "specific_data": {
            "precipitation_mm": precip_mm,
            "time_window_hours": window,
            "wind_speed_kmh": wind_speed,
            "wind_gusts_kmh": wind_gust,
            "weather_code": code,
        },
    }


def test_hourly_light_precipitation_is_low():
    result = calculate_precipitation_risk(
        PrecipitationInput(latitude=LAT, longitude=LON, time="t", precipitation_mm=5.0)
    )
    assert result.risk_level == "LOW"
    assert result.severity_score < 4.0


def test_hourly_intense_precipitation_is_high():
    result = calculate_precipitation_risk(
        PrecipitationInput(latitude=LAT, longitude=LON, time="t", precipitation_mm=25.0)
    )
    assert result.risk_level == "HIGH"
    assert result.severity_score >= 7.0


def test_24h_accumulation_heavy_is_high():
    result = calculate_precipitation_risk(
        PrecipitationInput(
            latitude=LAT,
            longitude=LON,
            time="t",
            precipitation_mm=90.0,
            time_window_hours=24,
        )
    )
    assert result.risk_level == "HIGH"


def test_thunderstorm_code_sets_high_floor():
    result = calculate_precipitation_risk(
        PrecipitationInput(
            latitude=LAT, longitude=LON, time="t", precipitation_mm=0.0, weather_code=95
        )
    )
    assert result.risk_level == "HIGH"
    assert result.severity_score >= 7.0


def test_high_wind_increases_severity_score():
    calm = calculate_precipitation_risk(
        PrecipitationInput(latitude=LAT, longitude=LON, time="t", precipitation_mm=5.0)
    )
    windy = calculate_precipitation_risk(
        PrecipitationInput(
            latitude=LAT,
            longitude=LON,
            time="t",
            precipitation_mm=5.0,
            wind_gusts_kmh=70.0,
        )
    )
    assert windy.severity_score > calm.severity_score


def test_affected_area_is_the_containing_grid_cell():
    output = process_precipitation_hazard(_hazard(25.0))
    assert output["affected_area"] == cell_at(DEFAULT_GRID_SPEC, LAT, LON).polygon()


def test_affected_area_is_a_square_not_a_circle():
    ring = process_precipitation_hazard(_hazard(25.0))["affected_area"]["coordinates"][0]
    assert len(ring) == 5
    assert ring[0] == ring[-1]


def test_affected_area_respects_custom_grid_spec():
    spec = GridSpec(cell_size_deg=0.25)
    output = process_precipitation_hazard(_hazard(25.0), spec=spec)
    assert output["affected_area"] == cell_at(spec, LAT, LON).polygon()
    assert output["affected_area"] != cell_at(DEFAULT_GRID_SPEC, LAT, LON).polygon()


def test_output_carries_required_metadata():
    output = process_precipitation_hazard(_hazard(25.0, hazard_id="open-meteo:abc"))
    assert output["hazard_id"] == "open-meteo:abc"
    assert output["hazard_type"] == "rainfall"
    assert output["risk_level"] == "HIGH"
    assert isinstance(output["severity_score"], float)
    assert output["calculated_at"]
    assert output["notes"]


def test_location_out_of_range_fails_loudly():
    with pytest.raises(ValueError):
        process_precipitation_hazard(_hazard(25.0, lat=91.0))


def test_missing_hazard_id_fails_loudly():
    hazard = _hazard(25.0)
    del hazard["id"]
    with pytest.raises(ValueError):
        process_precipitation_hazard(hazard)


def test_missing_coordinates_fails_loudly():
    hazard = _hazard(25.0)
    del hazard["latitude"]
    del hazard["longitude"]
    with pytest.raises(ValueError):
        process_precipitation_hazard(hazard)


def test_geojson_location_coordinates_are_used():
    hazard = _hazard(25.0)
    del hazard["latitude"]
    del hazard["longitude"]
    hazard["location"] = {"type": "Point", "coordinates": [LON, LAT]}
    output = process_precipitation_hazard(hazard)
    assert output["affected_area"] == cell_at(DEFAULT_GRID_SPEC, LAT, LON).polygon()


def test_source_defaults_to_open_meteo():
    hazard = _hazard(25.0)
    del hazard["source"]
    assert process_precipitation_hazard(hazard)["source"] == "open_meteo"


def test_source_is_preserved_when_provided():
    hazard = _hazard(25.0)
    hazard["source"] = "custom_source"
    assert process_precipitation_hazard(hazard)["source"] == "custom_source"
