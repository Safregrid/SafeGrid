from app.api import hazards
import pytest

from app.db import init_db, save_hazard, get_hazard
from app.ingestion.open_meteo import OpenMeteoClient
from app.models.hazard import Hazard


@pytest.mark.asyncio
async def test_open_meteo_hazard_persists_to_database():
    init_db()

    client = OpenMeteoClient()

    hazards = await client.fetch_precipitation(
        lat=14.617094,
        lon=74.844864
    )

    assert hazards
    assert all(isinstance(hazard, Hazard) for hazard in hazards)

    hazard = hazards[0]

    save_hazard(hazard)

    saved = get_hazard(hazard.id)

    assert saved is not None

    assert saved["id"] == hazard.id
    assert saved["hazard_type"] == hazard.hazard_type
    assert saved["source"] == hazard.source
    assert saved["probability"] == hazard.probability
    assert saved["specific_data"] == hazard.specific_data
    assert saved["latitude"] == hazard.location.coordinates[1]
    assert saved["longitude"] == hazard.location.coordinates[0]

    print("\nNumber of hazards:", len(hazards))
    print("\nHazard produced by Open-Meteo:")
    print(hazard)

    save_hazard(hazard)

    saved = get_hazard(hazard.id)

    print("\nHazard retrieved from DB:")
    print(saved)

    for hazard in hazards[:10]:
        print(
            hazard.timestamp,
            "precipitation=",
            hazard.specific_data["precipitation_mm"],
            "probability=",
            hazard.probability,
        )