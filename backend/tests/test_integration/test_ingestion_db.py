import pytest

from app.db import get_data_record, init_db, save_data_record
from app.ingestion.open_meteo import OpenMeteoClient
from app.models.data import DataRecord


@pytest.mark.asyncio
async def test_open_meteo_data_record_persists_to_database():
    init_db()

    client = OpenMeteoClient()

    records = await client.fetch_precipitation(
        lat=14.617094,
        lon=74.844864,
    )

    assert records
    assert all(isinstance(record, DataRecord) for record in records)

    record = records[0]

    save_data_record(record)

    saved = get_data_record(record.id)

    assert saved is not None

    assert saved["id"] == record.id
    assert saved["data_type"] == record.data_type
    assert saved["source"] == record.source
    assert saved["probability"] == record.probability
    assert saved["specific_data"] == record.specific_data
    assert saved["latitude"] == record.location.coordinates[1]
    assert saved["longitude"] == record.location.coordinates[0]