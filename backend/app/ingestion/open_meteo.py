"""
Open-Meteo weather/rainfall ingestion adapter.

Person 1 implements this module.

Responsibility:
- Fetch weather/rainfall forecasts from the Open-Meteo API — one point at a
  time (fetch_precipitation), or a whole grid region in one batch
  (fetch_precipitation_many)
- Normalize responses into DataRecords. Never Hazards: hazard identification
  happens downstream, in the risk subsystem.
- Handle HTTP errors and malformed responses gracefully
"""

from __future__ import annotations

class OpenMeteoError(Exception):
    """Raised when Open-Meteo data cannot be fetched or parsed."""

from datetime import datetime
from typing import Any

import httpx

from app.models.data import DataRecord
from app.models.hazard import GeoPoint


def split_grid_record_id(record_id: str) -> tuple[str, str]:
    """
    Split a grid DataRecord id back into (cell_id, iso_time).

    `Cell.cell_id` is `grid:<label>:<row>:<col>` (app/risk/grid.py), so a grid
    record id reads `grid:<label>:<row>:<col>:<iso_time>`.

    Splitting on the LAST colon would be wrong: the ISO time contains a colon of
    its own (`2026-10-08T00:00`). Split on the fourth instead, mirroring
    `grid.parse_cell_id`, which also requires exactly four `:`-separated parts.

    Raises ValueError when `record_id` is not a grid record id.
    """
    parts = record_id.split(":", 4)
    if len(parts) != 5 or parts[0] != "grid":
        raise ValueError(f"Malformed grid record id: {record_id!r}")
    return ":".join(parts[:4]), parts[4]


class OpenMeteoClient:
    """Client for fetching precipitation and weather forecasts from Open-Meteo."""

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    # Open-Meteo's documented cap on comma-separated coordinates per request.
    # Larger regions are split across several calls (see fetch_precipitation_many).
    MAX_LOCATIONS_PER_REQUEST = 1000

    async def fetch_precipitation(
        self,
        lat: float,
        lon: float,
    ) -> list[DataRecord]:
        """Fetch hourly weather/precipitation forecasts and normalize them to DataRecords."""

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
        except ValueError as exc:
            raise OpenMeteoError(
                "Open-Meteo returned an invalid response"
            ) from exc

        return self._hourly_records(
            data,
            lat=lat,
            lon=lon,
            id_prefix=f"open-meteo:{lat}:{lon}",
        )

    async def fetch_precipitation_many(
        self,
        coords: list[tuple[str, float, float]],
        *,
        forecast_days: int | None = None,
    ) -> list[DataRecord]:
        """
        Batch fetch for a grid run: one region, many cell centres.

        `coords` is exactly what `app.risk.rain_grid.cell_requests()` produces —
        (cell_id, latitude, longitude) tuples, in region order. Returns one
        DataRecord per cell per forecast hour, grouped in the same order as
        `coords`, with `id = "<cell_id>:<iso_time>"`.

        `forecast_days` is passed through to Open-Meteo. Left as None it keeps
        the API default of 7 days (168 hourly samples per cell), which is far
        more than `score_grid()` consumes — it only reads the first
        `window_hours`. Callers should set it just above their scoring window to
        avoid carrying thousands of unused records.

        The id does NOT add a "grid:" prefix of its own: `Cell.cell_id` is
        already `grid:<label>:<row>:<col>` (see app/risk/grid.py), so an extra
        prefix would produce `grid:grid:...`. Use `split_grid_record_id()` to
        recover the (cell_id, time) pair — do not split on the last colon, the
        ISO time contains one.

        IMPORTANT: these records are a transport format for the shared 3-tier
        flow, not events. Do NOT pass them to `pipeline.evaluate_and_store()` —
        a grid cell is never a hazard, and docs/OFFLINE.md reserves per-cell
        storage for the `grid_cells` table.
        """
        if not coords:
            return []

        records: list[DataRecord] = []
        for start in range(0, len(coords), self.MAX_LOCATIONS_PER_REQUEST):
            chunk = coords[start : start + self.MAX_LOCATIONS_PER_REQUEST]
            records.extend(await self._fetch_chunk(chunk, forecast_days=forecast_days))

        return records

    async def _fetch_chunk(
        self,
        chunk: list[tuple[str, float, float]],
        *,
        forecast_days: int | None = None,
    ) -> list[DataRecord]:
        """One batched Open-Meteo call covering up to MAX_LOCATIONS_PER_REQUEST cells."""
        params = {
            "latitude": ",".join(str(lat) for _, lat, _ in chunk),
            "longitude": ",".join(str(lon) for _, _, lon in chunk),
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

        if forecast_days is not None:
            params["forecast_days"] = forecast_days

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.BASE_URL,
                    params=params,
                    # A batch payload is far larger than a single point's; the
                    # 5s default is not reliably long enough to read one.
                    timeout=60.0,
                )

            response.raise_for_status()

        except httpx.RequestError as exc:
            raise OpenMeteoError("Failed to connect to Open-Meteo") from exc
        except httpx.HTTPStatusError as exc:
            raise OpenMeteoError(
                f"Open-Meteo returned HTTP {exc.response.status_code}"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise OpenMeteoError(
                "Open-Meteo returned an invalid response"
            ) from exc

        # Comma-separated coordinates come back as a JSON array, one element per
        # coordinate, in request order. Accept a bare object too, so a one-cell
        # run does not hinge on that detail.
        results = payload if isinstance(payload, list) else [payload]

        if len(results) != len(chunk):
            raise OpenMeteoError(
                "Open-Meteo returned "
                f"{len(results)} results for {len(chunk)} locations"
            )

        records: list[DataRecord] = []
        for (cell_id, lat, lon), result in zip(chunk, results):
            records.extend(
                self._hourly_records(
                    result,
                    lat=lat,
                    lon=lon,
                    id_prefix=cell_id,
                )
            )

        return records

    def _hourly_records(
        self,
        result: Any,
        *,
        lat: float,
        lon: float,
        id_prefix: str,
    ) -> list[DataRecord]:
        """
        Parse one Open-Meteo result object into one DataRecord per forecast hour.

        Shared by the single-point and the batch fetcher so both emit identical
        records; only the id prefix differs.
        """
        try:
            hourly = result["hourly"]
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

        records: list[DataRecord] = []

        for timestamp, amount, probability, wind_speed, wind_gust, weather_code in zip(
            times,
            precipitation,
            probabilities,
            wind_speeds,
            wind_gusts,
            weather_codes,
        ):
            records.append(
                DataRecord(
                    id=f"{id_prefix}:{timestamp}",
                    data_type="weather",
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

        return records