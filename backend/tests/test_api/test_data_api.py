from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.db import init_db, save_data_record
from app.main import app
from app.models.data import DataRecord
from app.models.hazard import GeoPoint


@pytest.fixture
def client():
    return TestClient(app)


def test_read_data_records(client):
    init_db()

    record = DataRecord(
        id="open-meteo:10.0:20.0:2026-10-09T12:00",
        data_type="weather",
        source="open_meteo",
        timestamp=datetime.now(timezone.utc),
        location=GeoPoint(coordinates=[20.0, 10.0]),
        magnitude=5.0,
        probability=20.0,
        specific_data={"precipitation_mm": 5.0},
    )
    save_data_record(record)

    response = client.get("/api/data")
    assert response.status_code == 200
    res_data = response.json()
    assert "records" in res_data
    assert len(res_data["records"]) >= 1

    rec_res = client.get(f"/api/data/{record.id}")
    assert rec_res.status_code == 200
    assert rec_res.json()["id"] == record.id
