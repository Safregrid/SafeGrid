"""
Stub: Open-Meteo weather/rainfall ingestion adapter.

Person 1 implements this module.

Responsibility:
- Fetch weather/rainfall data from the Open-Meteo API
- Normalize the response into a list of Hazard objects
- Handle HTTP errors and malformed responses gracefully
"""

from __future__ import annotations

class OpenMeteoError(Exception):
    """Raised when Open-Meteo data cannot be fetched or parsed."""

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
            "hourly": (
                "precipitation,"
                "precipitation_probability,"
                "wind_speed_10m,"
                "wind_gusts_10m,"
                "weather_code"
            ),
            "timezone": "UTC",
            "wind_speed_unit": "kmh",
            "precipitation_unit": "mm",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.BASE_URL,
                    params=params,
                )

            response.raise_for_status()

        except httpx.RequestError as exc:
            raise OpenMeteoError("Failed to connect to Open-Meteo") from exc
        except httpx.HTTPStatusError as exc:
            raise OpenMeteoError(
                f"Open-Meteo returned HTTP {exc.response.status_code}"
            ) from exc

        try:
            data: dict[str, Any] = response.json()
            hourly = data["hourly"]
            times = hourly["time"]
            precipitation = hourly["precipitation"]
            probabilities = hourly["precipitation_probability"]

        except (ValueError, KeyError, TypeError) as exc:
            raise OpenMeteoError(
                "Open-Meteo returned an invalid response"
            ) from exc
        
        if not (len(times) == len(precipitation) == len(probabilities)):
            raise OpenMeteoError(
                "Open-Meteo returned hourly arrays with different lengths"
            )
        
        wind_speeds = hourly.get("wind_speed_10m", [None] * len(times))
        wind_gusts = hourly.get("wind_gusts_10m", [None] * len(times))
        weather_codes = hourly.get("weather_code", [None] * len(times))

        hazards: list[Hazard] = []

        for timestamp, amount, probability, wind_speed, wind_gust, weather_code in zip(
            times,
            precipitation,
            probabilities,
            wind_speeds,
            wind_gusts,
            weather_codes,
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
                    magnitude=amount,
                    probability=probability,
                    specific_data={
                        "precipitation_mm": amount,
                        "wind_speed_kmh": wind_speed,
                        "wind_gusts_kmh": wind_gust,
                        "weather_code": weather_code,
                    },
                )
            )

        return hazards