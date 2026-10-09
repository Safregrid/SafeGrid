"""
Stub: Risk classifier and Hazard Identifier.

Person 2 implements this module.

Responsibility:
- Accept normalized DataRecord from ingestion or an identified Hazard
- Identify if a DataRecord represents a hazardous event/condition -> Hazard
- Apply hazard-specific rules to determine risk level -> RiskResult

⚠️  Before implementing: document thresholds in docs/RISK_MODEL.md.
    Do not invent scientifically meaningful thresholds without justification.
"""

from __future__ import annotations

from app.models.data import DataRecord
from app.models.hazard import Hazard, RiskResult


def identify_hazard(data: DataRecord) -> Hazard | None:
    """
    Identifies whether a raw provider DataRecord constitutes an active/potential Hazard.

    Person 2 defines hazard identification rules/thresholds in docs/RISK_MODEL.md.
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

# TODO (Person 2): implement classify(hazard: Hazard) -> RiskResult
#
# Suggested structure:
#
#   def classify(hazard: Hazard) -> RiskResult:
#       if hazard.hazard_type == "earthquake":
#           return _classify_earthquake(hazard)
#       elif hazard.hazard_type == "rainfall" or hazard.hazard_type == "weather":
#           return _classify_rainfall(hazard)
#       else:
#           raise ValueError(f"Unknown hazard type: {hazard.hazard_type}")

