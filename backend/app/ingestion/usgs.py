"""
Stub: USGS earthquake ingestion adapter.

Person 1 implements this module.

Responsibility:
- Fetch from the USGS GeoJSON feed
- Normalize the response into a list of Hazard objects
- Handle HTTP errors and malformed responses gracefully
"""

from __future__ import annotations

# TODO (Person 1): implement USGSClient
# Suggested interface:
#
#   class USGSClient:
#       async def fetch_recent(self, timeframe: str = "hour") -> list[Hazard]:
#           ...
#
# Reference feed: https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php
# No API key required.
