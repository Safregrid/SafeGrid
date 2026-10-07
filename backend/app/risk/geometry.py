"""
Stub: Affected-area geometry computation.

Person 2 implements this module.

Responsibility:
- Accept a Hazard object and severity score
- Compute a GeoJSON geometry representing the affected area
- Return the geometry dict (Polygon, MultiPolygon, etc.)

⚠️  Do not use a generic circular buffer for all hazard types.
    The geographic model must be appropriate for each hazard.
    Document the choice in docs/RISK_MODEL.md.
"""

from __future__ import annotations

from app.models.hazard import Hazard

# TODO (Person 2): implement compute_affected_area(hazard, severity) -> dict
#
# The returned dict must be a valid GeoJSON geometry object.
# Coordinate order: [longitude, latitude] (GeoJSON spec).
