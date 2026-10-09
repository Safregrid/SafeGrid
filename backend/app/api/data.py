"""
Minimal /api/data router for normalized provider data records.

Person 1 implements this module.
Register this router in app/main.py.
"""

from fastapi import APIRouter, HTTPException, Query

from app.db.repository import get_data_record, list_data_records

router = APIRouter(prefix="/data", tags=["data"])


@router.get("")
def read_data_records(
    limit: int = Query(default=50, ge=1, le=500),
) -> dict:
    records = list_data_records(limit=limit)

    return {
        "records": records,
    }


@router.get("/{record_id}")
def read_data_record(record_id: str) -> dict:
    record = get_data_record(record_id)

    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"Data record '{record_id}' not found",
        )

    return record
