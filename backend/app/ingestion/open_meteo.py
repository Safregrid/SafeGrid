"""
Stub: Open-Meteo weather/rainfall ingestion adapter.

Person 1 implements this module.

Responsibility:
- Fetch weather/rainfall data from the Open-Meteo API
- Normalize the response into a list of Hazard objects
- Handle HTTP errors and malformed responses gracefully
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.models.hazard import GeoPoint, Hazard


class OpenMeteoClient:
    """Client for fetching precipitation forecasts from Open-Meteo."""

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    async def fetch_precipitation(
        self,
        lat: float,
        lon: float,
    ) -> list[Hazard]:
        """Fetch hourly precipitation forecasts and normalize them to Hazards."""

        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "precipitation,precipitation_probability",
            "timezone": "UTC",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.BASE_URL,
                params=params,
            )

        response.raise_for_status()

        data: dict[str, Any] = response.json()
        hourly = data["hourly"]

        times = hourly["time"]
        precipitation = hourly["precipitation"]
        probabilities = hourly["precipitation_probability"]

        hazards: list[Hazard] = []

        for timestamp, amount, probability in zip(
            times,
            precipitation,
            probabilities,
        ):
            hazards.append(
                Hazard(
                    id=f"open-meteo:{lat}:{lon}:{timestamp}",
                    hazard_type="rainfall",
                    source="open_meteo",
                    timestamp=datetime.fromisoformat(timestamp),
                    location=GeoPoint(
                        coordinates=[lon, lat],
                    ),
                    magnitude=None,
                    probability=probability,
                    duration=None,
                    specific_data={
                        "precipitation_mm": amount,
                    },
                )
            )

        return hazards