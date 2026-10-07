"""
Stub: Open-Meteo weather/rainfall ingestion adapter.

Person 1 implements this module.

Responsibility:
- Fetch weather/rainfall data from the Open-Meteo API
- Normalize the response into a list of Hazard objects
- Handle HTTP errors and malformed responses gracefully
"""

from __future__ import annotations

# TODO (Person 1): implement OpenMeteoClient
# Suggested interface:
#
#   class OpenMeteoClient:
#       async def fetch_precipitation(self, lat: float, lon: float) -> Hazard:
#           ...
#
# Reference: https://open-meteo.com/en/docs
# No API key required for the free tier.
