import pytest

from app.ingestion.open_meteo import OpenMeteoClient


@pytest.mark.asyncio
async def test_fetch_precipitation():
    client = OpenMeteoClient()

    hazards = await client.fetch_precipitation(
        lat=28.6139,
        lon=77.2090,
    )

    assert len(hazards) > 0

    hazard = hazards[0]

    assert hazard.hazard_type == "rainfall"
    assert hazard.source == "open_meteo"
    assert hazard.location.coordinates == [77.2090, 28.6139]
    assert 0 <= hazard.probability <= 100
    assert "precipitation_mm" in hazard.specific_data