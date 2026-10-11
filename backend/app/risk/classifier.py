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


# Provider-specific data_type labels -> SafeGrid's canonical hazard_type vocabulary.
# Providers name things their own way (Open-Meteo feeds precipitation under
# data_type="weather"); this table is the single place that translates them.
# Agree new entries with Person 1 and document them in docs/RISK_MODEL.md.
RAW_TYPE_TO_HAZARD_TYPE: dict[str, str] = {
    "weather": "rainfall",    # Open-Meteo hourly precipitation/weather feed
    "seismic": "earthquake",  # USGS earthquake feed (when implemented)
}


def map_data_type_to_hazard_type(data_type: str) -> str | None:
    """
    Translates a provider's raw data_type label into SafeGrid's canonical
    hazard_type. Returns None for an unrecognised label so callers can skip
    records we do not yet classify instead of raising.
    """
    return RAW_TYPE_TO_HAZARD_TYPE.get(data_type)


def identify_hazard(data: DataRecord) -> Hazard | None:
    """
    Identifies whether a raw provider DataRecord constitutes an active/potential Hazard.

    The provider's data_type label is translated to a canonical hazard_type via
    RAW_TYPE_TO_HAZARD_TYPE. Records whose label is not mapped are skipped
    (returns None) rather than raising.

    TODO: Person 2 defines hazard identification rules/thresholds in docs/RISK_MODEL.md.
    """
    hazard_type = map_data_type_to_hazard_type(data.data_type)
    if hazard_type is None:
        return None

    return Hazard(
        id=data.id,
        hazard_type=hazard_type,
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