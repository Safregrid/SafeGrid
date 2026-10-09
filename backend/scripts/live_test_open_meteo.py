"""
Live integration check for SafeGrid's Open-Meteo ingestion and DataRecord persistence.

Run from the backend directory:
    python scripts/live_test_open_meteo.py

This test makes a real request to Open-Meteo and writes at most two records
to the configured SafeGrid database. It does not delete or reset existing data.
"""

import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db import get_data_record, init_db, save_data_record
from app.ingestion.open_meteo import OpenMeteoClient, OpenMeteoError
from app.models.data import DataRecord

LATITUDE = 12.9716
LONGITUDE = 77.5946
MAX_RECORDS_TO_SAVE = 2


async def main() -> int:
    print("SafeGrid live Open-Meteo ingestion test")
    print(f"Location: latitude={LATITUDE}, longitude={LONGITUDE}")
    print("Requesting live forecast data from Open-Meteo...")

    try:
        client = OpenMeteoClient()
        records = await client.fetch_precipitation(
            lat=LATITUDE,
            lon=LONGITUDE,
        )
    except OpenMeteoError as exc:
        print(f"FAIL: Open-Meteo ingestion failed: {exc}")
        return 1
    except Exception as exc:
        print(f"FAIL: Unexpected error while fetching data: {exc}")
        return 1

    if not records:
        print("FAIL: Open-Meteo returned no records.")
        return 1

    print(f"PASS: Received {len(records)} live records.")

    for record in records:
        assert isinstance(record, DataRecord), (
            f"Expected DataRecord, got {type(record).__name__}"
        )
        assert record.source == "open_meteo", (
            f"Unexpected source: {record.source!r}"
        )
        assert record.location.coordinates == [LONGITUDE, LATITUDE], (
            f"Unexpected coordinate order/values: {record.location.coordinates!r}"
        )
        if record.probability is not None:
            assert 0 <= record.probability <= 100, (
                f"Probability outside 0-100 range: {record.probability}"
            )

    print("PASS: Record types, source, coordinates, and probability scale verified.")

    init_db()

    # Persist only a small sample; do not reset or delete the existing database.
    records_to_save = records[:MAX_RECORDS_TO_SAVE]
    for record in records_to_save:
        save_data_record(record)
        saved = get_data_record(record.id)

        assert saved is not None, f"Record was not retrievable after saving: {record.id}"
        assert saved["id"] == record.id
        assert saved["data_type"] == record.data_type
        assert saved["source"] == record.source
        assert saved["specific_data"] == record.specific_data
        assert saved["latitude"] == record.location.coordinates[1]
        assert saved["longitude"] == record.location.coordinates[0]

        if record.probability is not None:
            assert saved["probability"] == record.probability
        if record.magnitude is not None:
            assert saved["magnitude"] == record.magnitude

        print(f"PASS: Saved and retrieved {record.id}")

    print(
        f"SUCCESS: Live fetch passed; {len(records_to_save)} record(s) "
        "were persisted and verified."
    )
    print("This script does not verify the running HTTP API.")
    print("Check GET /api/data separately while the FastAPI server is running.")
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
    except AssertionError as exc:
        print(f"FAIL: Verification assertion failed: {exc}")
        exit_code = 1
    raise SystemExit(exit_code)
