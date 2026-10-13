"""
/api/risk-zones: publishes persisted risk results as a GeoJSON
FeatureCollection for Person 3's MapLibre map.

Person 1 implements this module (wiring). Person 2 produces the
affected_area geometry via the risk engine.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.db.repository import list_hazards_with_risk

router = APIRouter(prefix="/risk-zones", tags=["risk-zones"])

# Valid GeoJSON geometry types a zone can render. Anything else = row we can't draw.
_ZONE_TYPES = ("Polygon", "MultiPolygon")

def _to_feature(row: dict) -> dict | None:
    """
    Convert one DB row (hazard LEFT JOIN risk_results) into a GeoJSON Feature.

    Returns None for rows with no drawable geometry — a hazard without a
    risk result (LEFT JOIN) is NOT a zone, and an invalid geometry would
    produce broken GeoJSON.
    """
    geometry = row.get("affected_area")
    if not isinstance(geometry, dict) or geometry.get("type") not in _ZONE_TYPES:
        return None

    return{
        "type": "Feature",
        "geometry": geometry,
        "properties": {
            "hazard_id": row["id"],
            "hazard_type" : row.get("hazard_type"),
            "risk_level": row.get("risk_level"), # HIGH | MODERATE | LOW
            "severity_score": row.get("severity_score"),  # 0.0 - 10.0
            # NOTE: list_hazards_with_risk() doesn't select r.calculated_at yet.
            # Ask P4 to add it to the JOIN's SELECT; until then it's None and
            # the frontend falls back to a neutral rendering.
            "calculated_at": row.get("calculated_at"),
            "is_live": False,  # No live ingestion is wired yet, so honest default is False.
            # When data-freshness lands (P4's offline layer), derive this from
            # the ingestion timestamp instead of hardcoding.
        },
    }

@router.get("")
def read_risk_zones(
    limit: int = Query(default=50, ge=1, le=500),
) -> dict:
    rows = list_hazards_with_risk(limit=limit)

    features = [
        feature
        for feature in (_to_feature(row) for row in rows)
        if feature is not None
    ]

    return {
        "type": "FeatureCollection",
        "features": features,
    }





