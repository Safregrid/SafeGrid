"""
Risk classifier engine and Hazard Identifier for SafeGrid.

Owner: Person 2 (Risk Engine & Geospatial Processing)
Branch: feature/risk-engine
(merged into feature/data-ingestion)

Responsibility:
- Accept a normalized DataRecord from Person 1's ingestion layer and identify
  whether it represents a hazardous event/condition (identify_hazard -> Hazard).
- Accept a Hazard object and apply hazard-specific rules to determine risk
  level and affected area (classify -> RiskResult).

⚠️  Thresholds must be documented in docs/RISK_MODEL.md.
    Do not invent scientifically meaningful thresholds without justification.
"""

from __future__ import annotations

from datetime import datetime

from app.models.data import DataRecord
from app.models.hazard import Hazard, RiskResult
from app.risk import rain


def identify_hazard(data: DataRecord) -> Hazard | None:
    """
    Identifies whether a raw provider DataRecord constitutes an active/potential Hazard.

    TODO: Person 2 defines hazard identification rules/thresholds in docs/RISK_MODEL.md.
    TODO: the hazard_type mapping (e.g. "weather" -> "rainfall") must be agreed
          between Person 1 and Person 2 so identify_hazard output feeds classify().
    """
    # Placeholder: convert DataRecord into a Hazard if hazardous conditions exist.
    # To be implemented by Person 2 based on RISK_MODEL.md thresholds.
    return Hazard(
        id=data.id,
        hazard_type=data.data_type,
        source=data.source,
        timestamp=data.timestamp,
        location=data.location,
        magnitude=data.magnitude,
        probability=data.probability,
        specific_data=data.specific_data,
    )


def _classify_rainfall(hazard: Hazard) -> RiskResult:
    """Classifies rainfall hazard using the precipitation risk engine in rain.py."""
    res_dict = rain.process_precipitation_hazard(hazard)

    calc_at = datetime.fromisoformat(res_dict["calculated_at"])

    return RiskResult(
        hazard_id=res_dict["hazard_id"],
        risk_level=res_dict["risk_level"],
        severity_score=res_dict["severity_score"],
        affected_area=res_dict["affected_area"],
        calculated_at=calc_at,
        notes=res_dict["notes"],
    )


def classify(hazard: Hazard) -> RiskResult:
    """
    Evaluates a normalized hazard and produces a validated RiskResult.
    """
    if hazard.hazard_type == "rainfall":
        return _classify_rainfall(hazard)
    else:
        # TODO(open): "weather" hazards from Open-Meteo ingestion currently
        # raise here — agree the data_type -> hazard_type mapping with Person 1.
        # Person 2 will create a separate file for earthquakes etc.
        raise NotImplementedError(
            f"Classification for hazard type '{hazard.hazard_type}' will be added in a separate module."
        )