"""
Internal data models shared across subsystems.

These are NOT database models and NOT API response schemas.
They are the internal representation that Person 1 produces
and Person 2 consumes.

⚠️  OPEN: exact fields must be agreed between Person 1 and Person 2
          before implementation begins. Update this file when agreed.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class GeoPoint(BaseModel):
    """GeoJSON Point (longitude, latitude)."""

    type: str = "Point"
    coordinates: list[float]  # [longitude, latitude]


class Hazard(BaseModel):
    """
    Normalized representation of a hazard event.

    Produced by: Person 1 (ingestion layer).
    Consumed by: Person 2 (risk engine) and Person 4 (database layer).
    """

    id: str
    hazard_type: str          # e.g. "earthquake", "rainfall"
    source: str               # e.g. "usgs", "open_meteo"
    timestamp: datetime
    location: GeoPoint
    specific_data: dict[str, Any] = Field(default_factory=dict) # hazard specific normalised fields
    probability: float | None = None
    duration: float | None = None    


class RiskResult(BaseModel):
    """
    Risk classification result for a hazard event.

    Produced by: Person 2 (risk engine).
    Consumed by: Person 1 (API layer), Person 4 (database layer).

    ⚠️  OPEN: geometry type (Polygon, MultiPolygon, FeatureCollection)
              is not decided yet. Placeholder is dict for now.
    """

    hazard_id: str
    risk_level: str           # "HIGH" | "MODERATE" | "LOW"
    severity_score: float
    affected_area: dict       # GeoJSON geometry — exact type TBD
    calculated_at: datetime
    notes: str | None = None  # reference to threshold justification
