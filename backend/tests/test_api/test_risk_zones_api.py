from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.db.repository import init_db
from app.main import app
from app.models.data import DataRecord
from app.models.hazard import GeoPoint
from app.risk.pipeline import evaluate_and_store


@pytest.fixture
def client():
    return TestClient(app)


def _weather_record(precip_mm: float = 25.0) -> DataRecord:
    """A realistic Open-Meteo-shaped record (IMD intense spell: 20-30 mm/h)."""
    return DataRecord(
        id="open-meteo:test:12.97:77.6",
        data_type="weather",
        source="open_meteo",
        timestamp=datetime.now(timezone.utc),
        location=GeoPoint(coordinates=[77.6, 12.97]),
        magnitude=precip_mm,
        probability=80.0,
        specific_data={
            "precipitation_mm": precip_mm,
            "wind_speed_kmh": 20.0,
            "wind_gusts_kmh": 25.0,
            "weather_code": 63,  # moderate rain
        },
    )


def test_pipeline_weather_record_yields_risk_result(client):
    """Whole chain (no HTTP): DataRecord -> classify -> RiskResult dict."""
    init_db()

    result = evaluate_and_store(_weather_record())

    assert result is not None
    assert result["risk_level"] in ("HIGH", "MODERATE", "LOW")
    assert 0.0 <= result["severity_score"] <= 10.0
    assert result["affected_area"]["type"] == "Polygon"


def test_read_risk_zones_returns_feature_collection(client):
    """Seeded via the pipeline, served via the HTTP endpoint."""
    init_db()

    evaluate_and_store(_weather_record())

    response = client.get("/api/risk-zones")
    assert response.status_code == 200

    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) == 1

    feature = body["features"][0]
    assert feature["geometry"]["type"] == "Polygon"
    assert feature["properties"]["hazard_id"].startswith("open-meteo:")
    assert feature["properties"]["risk_level"] in ("HIGH", "MODERATE", "LOW")


def test_risk_zones_empty_when_nothing_classified(client):
    """No hazard, no zones — but still a valid, empty FeatureCollection."""
    init_db()

    response = client.get("/api/risk-zones")
    assert response.status_code == 200

    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert body["features"] == []