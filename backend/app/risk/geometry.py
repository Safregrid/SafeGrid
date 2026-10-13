"""
Affected-area geometry toolkit for SafeGrid.

Owner: Person 2 (Risk Engine & Geospatial Processing)
Branch: feature/risk-engine

Shared, hazard-agnostic GeoJSON geometry primitives composed by the risk engines
(rain.py, earthquake.py). This module holds NO hazard knowledge — it draws
shapes; the engines decide the radii/thresholds that feed it.

Coordinate convention: RFC 7946 GeoJSON, [longitude, latitude], closed rings.
"""

from __future__ import annotations

import math
from typing import Any, Iterable


def point_circle(
    latitude: float,
    longitude: float,
    radius_km: float,
    num_points: int = 16,
) -> dict[str, Any]:
    """
    Draws a closed GeoJSON Polygon approximating a circle of `radius_km`
    centred on [longitude, latitude], using a local flat-earth approximation.

    Latitude is clamped to +/-89.9 to avoid division by zero near the poles and
    longitude is normalized to [-180, 180]. The ring is closed (first point ==
    last) as required by the GeoJSON specification.
    """
    lat_clamped = max(-89.9, min(89.9, float(latitude)))
    lon_clamped = float(longitude)

    km_per_deg_lat = 111.32
    cos_lat = max(0.0001, math.cos(math.radians(lat_clamped)))
    km_per_deg_lon = 111.32 * cos_lat

    delta_lat = radius_km / km_per_deg_lat
    delta_lon = radius_km / km_per_deg_lon

    ring: list[list[float]] = []
    for i in range(num_points):
        angle = (2.0 * math.pi * i) / num_points
        pt_lat = round(lat_clamped + delta_lat * math.sin(angle), 6)
        pt_lon = round(lon_clamped + delta_lon * math.cos(angle), 6)
        pt_lon = round((pt_lon + 180.0) % 360.0 - 180.0, 6)
        ring.append([pt_lon, pt_lat])

    ring.append(ring[0])

    return {
        "type": "Polygon",
        "coordinates": [ring],
    }


def compute_rainfall_polygon(
    latitude: float,
    longitude: float,
    severity_score: float,
    num_points: int = 16,
) -> dict[str, Any]:
    """
    Closed GeoJSON Polygon for the precipitation/runoff impact footprint around
    a point. The radius scales with the severity score:

    - Low Risk (< 4.0): ~3 km to 5 km buffer (localized shower / grid-cell footprint).
    - Moderate Risk (4.0 - 6.9): ~5 km to 10 km buffer (drainage / waterlogging zone).
    - High Risk (>= 7.0): ~10 km to 20 km buffer (flash-flood catchment & storm cell).

    ⚠️ This radius scaling is a heuristic, not a sourced physical relation; see
    docs/RISK_MODEL.md (affected-area section).
    """
    score = max(0.0, min(10.0, float(severity_score)))
    if score < 4.0:
        radius_km = 3.0 + (score / 4.0) * 2.0
    elif score < 7.0:
        radius_km = 5.0 + ((score - 4.0) / 3.0) * 5.0
    else:
        radius_km = 10.0 + ((score - 7.0) / 3.0) * 10.0

    return point_circle(latitude, longitude, radius_km, num_points=num_points)


def concentric_rings(
    latitude: float,
    longitude: float,
    radii_km: Iterable[float],
    num_points: int = 24,
) -> list[dict[str, Any]]:
    """
    Builds nested circles (one closed GeoJSON Polygon per radius) around a point.

    Intended for the earthquake engine, where the radii come from a ground-motion
    attenuation relation's MMI contour distances (not invented steps). Radii are
    returned in the order given; pass them ascending (smallest = highest intensity
    first). The nested circles intentionally overlap — to render disjoint intensity
    *bands* (annuli) take the difference of consecutive rings upstream.
    """
    return [
        point_circle(latitude, longitude, float(radius_km), num_points=num_points)
        for radius_km in radii_km
    ]
