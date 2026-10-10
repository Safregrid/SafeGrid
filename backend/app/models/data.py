"""
Normalized raw data collected from external providers.

Produced by: Ingestion layer (e.g. Person 1).
Consumed by: Hazard Identification / Risk Subsystem (Person 2) and Persistence Layer (Person 4).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.hazard import GeoPoint


class DataRecord(BaseModel):
    """
    Generic normalized observation or forecast received from external providers.

    Distinct from a Hazard: a DataRecord contains raw environmental readings/forecasts,
    which may or may not be identified as a hazardous event.
    """

    id: str
    data_type: str             # e.g. "weather", "seismic", "flood"
    source: str                # e.g. "open_meteo", "usgs"
    timestamp: datetime
    location: GeoPoint
    magnitude: float | None = None       # raw measurement magnitude if applicable
    probability: float | None = None     # forecast probability (0 to 100%)
    specific_data: dict[str, Any] = Field(default_factory=dict)
