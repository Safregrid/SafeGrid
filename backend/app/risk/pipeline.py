"""
Pipeline: connects the risk engine to DB and API callers.

Flow: DataRecord -> identify_hazard() -> Hazard -> classify() -> RiskResult

Person 1 implements this module (wiring). Person 2 owns the engine pieces.
"""

from __future__ import annotations

from typing import Any

from app.db.repository import save_hazard, save_risk_result
from app.models.data import DataRecord
from app.risk.classifier import classify, identify_hazard

def evaluate(record: DataRecord) -> dict[str, Any] | None:
    """
    Push one DataRecord through the whole risk chain WITHOUT touching the DB.

    Returns the RiskResult as a dict, or None when the record isn't a
    hazard we classify (identify_hazard() already skips unmapped types).
    """

    hazard = identify_hazard(record)
    if hazard is None:
        return None
    result = classify(hazard)
    return result.model_dump()


def evaluate_and_store(record: DataRecord, database=None) -> dict[str, Any] | None:
    """
    evaluate() + persist both the hazard and its risk result.
    Returns the persisted risk_result row (dict) or None if skipped.
    database kwarg mirrors the repository functions (defaults to the app db).
    """

    hazard = identify_hazard(record)
    if hazard is None:
        return None

    result = classify(hazard)

    # save_hazard uses ON CONFLICT DO UPDATE so the risk_results row
    # (FK with ON DELETE CASCADE) is NOT destroyed on re-evaluation.

    save_hazard(hazard, database=database)
    return save_risk_result(result, database=database)


