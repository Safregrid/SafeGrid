"""
Turning a granted location into a grid region.

Person 1 owns this module. It answers the question a real user raises: "I am
standing in <my village> — what do you score for me?"

SafeGrid does not know anyone's village boundary, and does not pretend to.
Reliable village outlines are not something we can depend on (OpenStreetMap
coverage is patchy across rural Karnataka, and a wrong outline would silently
score the wrong ground while looking authoritative). So instead we declare a
radius and are honest about it: model a fixed circle around wherever the user
stands, and say that is what we did.

This is a COVERAGE parameter, not a risk threshold — it decides what we look
at, never how dangerous something is. It is declared here with its
justification rather than buried in code, per docs/RISK_MODEL.md § 4.1.

§ 4 of docs/RISK_MODEL.md forbids circular geometry for hazard footprints.
That rule is respected: this radius produces the bounding box of a GRID of
square cells. No circle is ever drawn or returned.
"""

from __future__ import annotations

import math

from app.risk.grid import Region

# One degree of latitude is 1/360th of Earth's circumference (40 075 km at the
# equator) — a physical constant, not a tuned value. Longitude degrees shrink
# with latitude by cos(lat), which is why the two scales below differ.
KM_PER_DEGREE_LAT = 40075.0 / 360.0  # ≈ 111.32 km

# Within a degree of a pole, cos(lat) → 0 and the longitude span explodes.
# Refusing loudly beats scoring a wildly distorted strip of ground.
MAX_ABS_LATITUDE = 89.0


def region_around(
    latitude: float,
    longitude: float,
    radius_km: float,
    *,
    name: str | None = None,
) -> Region:
    """
    The bounding box enclosing a `radius_km` circle around one point.

    Because the box is scored rather than the circle, its corners lie up to
    √2 × `radius_km` from the centre. That is stated plainly rather than
    trimmed away: a grid can only ever be squares.
    """
    if radius_km <= 0:
        raise ValueError("radius_km must be positive")
    if abs(latitude) >= MAX_ABS_LATITUDE:
        raise ValueError(
            f"latitude {latitude} lies within 1° of a pole, where longitude "
            "degrees collapse towards zero. Refusing rather than scoring a "
            "distorted region."
        )
    if not -180.0 <= longitude <= 180.0:
        raise ValueError("longitude must be within [-180, 180]")

    degrees_lat = radius_km / KM_PER_DEGREE_LAT
    degrees_lon = radius_km / (KM_PER_DEGREE_LAT * math.cos(math.radians(latitude)))

    return Region(
        name=name or f"around-{latitude:.4f},{longitude:.4f}",
        min_lat=latitude - degrees_lat,
        max_lat=latitude + degrees_lat,
        min_lon=longitude - degrees_lon,
        max_lon=longitude + degrees_lon,
    )
