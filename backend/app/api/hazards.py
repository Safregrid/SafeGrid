"""
Stub: /api/hazards router.

Person 1 implements this module.
Register this router in app/main.py when ready.
"""

from fastapi import APIRouter, HTTPException, Query

from app.db.repository import get_hazard, list_hazards

router = APIRouter(prefix="/hazards", tags=["hazards"])


@router.get("")
def read_hazards(
    limit: int = Query(default=50, ge=1, le=500),
) -> dict:
    hazards = list_hazards(limit=limit)

    return {
        "is_live": False,
        "hazards": hazards,
    }


@router.get("/{hazard_id}")
def read_hazard(hazard_id: str) -> dict:
    hazard = get_hazard(hazard_id)

    if hazard is None:
        raise HTTPException(
            status_code=404,
            detail=f"Hazard '{hazard_id}' not found",
        )

    return hazard