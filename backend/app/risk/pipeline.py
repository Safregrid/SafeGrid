"""
Risk pipeline seam for SafeGrid.

Owner: Person 2 (Risk Engine & Geospatial Processing)
Branch: feature/risk-engine

Connects the ingestion layer's normalized DataRecords to the risk engine and
persistence layer:

    DataRecord -> identify_hazard() -> Hazard -> classify() -> RiskResult
                                                          -> save_hazard()
                                                          -> save_risk_result()

This is the single entry point callers (Person 1's ingestion wiring, a scheduled
job, or the API layer) use to run the engine. It stays within Person 2's scope:
it composes the classifier and the Person 4 repository, and adds no hazard logic.

Note: a DataRecord whose data_type maps to a hazard we do not yet classify
(e.g. "seismic" -> "earthquake" before earthquake.py exists) will raise
NotImplementedError from classify(). This is deliberate — we fail loudly rather
than silently skip a hazard type that has been explicitly declared in
RAW_TYPE_TO_HAZARD_TYPE. Unmapped data_type labels are skipped (return None).
"""

from __future__ import annotations

from app.db import Database, db, save_hazard, save_risk_result
from app.models.data import DataRecord
from app.models.hazard import RiskResult
from app.risk.classifier import classify, identify_hazard


def evaluate(record: DataRecord) -> RiskResult | None:
    """
    Runs the engine on a single DataRecord without persisting anything.

    Returns the RiskResult, or None if the record's data_type is not mapped to
    a hazard type we handle.
    """
    hazard = identify_hazard(record)
    if hazard is None:
        return None
    return classify(hazard)


def evaluate_and_store(record: DataRecord, database: Database = db) -> RiskResult | None:
    """
    Runs the engine on a single DataRecord and persists the Hazard + RiskResult.

    Classification happens before any writes, so a classification failure leaves
    the database untouched. Returns the stored RiskResult, or None if the record's
    data_type is not mapped to a hazard type we handle.
    """
    hazard = identify_hazard(record)
    if hazard is None:
        return None

    result = classify(hazard)
    save_hazard(hazard, database=database)
    save_risk_result(result, database=database)
    return result


def evaluate_all(records: list[DataRecord]) -> list[RiskResult]:
    """
    Runs the engine over many DataRecords without persisting, skipping records
    whose data_type is unmapped. Returns the results in input order.
    """
    results: list[RiskResult] = []
    for record in records:
        result = evaluate(record)
        if result is not None:
            results.append(result)
    return results


def evaluate_and_store_all(
    records: list[DataRecord], database: Database = db
) -> list[RiskResult]:
    """
    Runs the engine over many DataRecords and persists each Hazard + RiskResult,
    skipping records whose data_type is unmapped. Returns the stored results.
    """
    results: list[RiskResult] = []
    for record in records:
        result = evaluate_and_store(record, database=database)
        if result is not None:
            results.append(result)
    return results
