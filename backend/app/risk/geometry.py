"""
Affected-area geometry computation for SafeGrid.
Owner: Person 2 (Risk Engine & Geospatial Processing)
Branch: feature/risk-engine

Computes GeoJSON geometry objects (Polygon) representing the
geographic hazard area for MapLibre rendering (Person 3) and DB persistence (Person 4).
"""

from __future__ import annotations

import math
from typing import Any

from app.models.hazard import Hazard


def compute_rainfall_polygon(
    latitude: float,
    longitude: float,
    severity_score: float,
    num_points: int = 16,
) -> dict[str, Any]:
    """
    Computes a closed GeoJSON Polygon representing the precipitation and runoff impact zone.

    The radius scales deterministically with severity score:
    - Low Risk (< 4.0): ~3 km to 5 km buffer (localized shower / grid cell footprint).
    - Moderate Risk (4.0 - 6.9): ~5 km to 10 km buffer (drainage / waterlogging zone).
    - High Risk (>= 7.0): ~10 km to 20 km buffer (flash flood catchment & storm cell).

    Coordinates are formatted as [longitude, latitude] in accordance with RFC 7946 GeoJSON.
    The first and last coordinate points are identical to form a closed linear ring.
    """
    score = max(0.0, min(10.0, float(severity_score)))
    if score < 4.0:
        radius_km = 3.0 + (score / 4.0) * 2.0
    elif score < 7.0:
        radius_km = 5.0 + ((score - 4.0) / 3.0) * 5.0
    else:
        radius_km = 10.0 + ((score - 7.0) / 3.0) * 10.0

    lat_rad = math.radians(latitude)
    km_per_deg_lat = 111.32
    # Prevent division by zero near poles
    cos_lat = max(0.0001, math.cos(lat_rad))
    km_per_deg_lon = 111.32 * cos_lat

    delta_lat = radius_km / km_per_deg_lat
    delta_lon = radius_km / km_per_deg_lon

    ring: list[list[float]] = []
    for i in range(num_points):
        angle = (2.0 * math.pi * i) / num_points
        pt_lat = round(latitude + delta_lat * math.sin(angle), 6)
        pt_lon = round(longitude + delta_lon * math.cos(angle), 6)
        ring.append([pt_lon, pt_lat])

    # Close the polygon ring as required by GeoJSON specification
    ring.append(ring[0])

    return {
        "type": "Polygon",
        "coordinates": [ring],
    }


def compute_affected_area(hazard: Hazard | dict[str, Any], severity: float) -> dict[str, Any]:
    """
    Computes a valid GeoJSON geometry representing the hazard's affected geographic area.
    Coordinate order: [longitude, latitude] (GeoJSON spec).
    """
    if hasattr(hazard, "model_dump"):
        data = hazard.model_dump()
    elif isinstance(hazard, dict):
        data = hazard
    else:
        data = dict(hazard)

    # Extract coordinates
    lat = data.get("latitude")
    lon = data.get("longitude")
    if lat is None or lon is None:
        loc = data.get("location")
        if isinstance(loc, dict):
            coords = loc.get("coordinates", [0.0, 0.0])
            lon, lat = coords[0], coords[1]
        elif hasattr(loc, "coordinates"):
            coords = loc.coordinates
            lon, lat = coords[0], coords[1]

    latitude = float(lat if lat is not None else 0.0)
    longitude = float(lon if lon is not None else 0.0)

    return compute_rainfall_polygon(latitude, longitude, severity)
