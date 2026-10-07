"""
Stub: Risk classifier.

Person 2 implements this module.

Responsibility:
- Accept a Hazard object (from Person 1's ingestion layer)
- Apply hazard-specific rules to determine risk level
- Return a RiskResult object

⚠️  Before implementing: document thresholds in docs/RISK_MODEL.md.
    Do not invent scientifically meaningful thresholds without justification.
"""

from __future__ import annotations

from app.models.hazard import Hazard, RiskResult

# TODO (Person 2): implement classify(hazard: Hazard) -> RiskResult
#
# Suggested structure:
#
#   def classify(hazard: Hazard) -> RiskResult:
#       if hazard.hazard_type == "earthquake":
#           return _classify_earthquake(hazard)
#       elif hazard.hazard_type == "rainfall":
#           return _classify_rainfall(hazard)
#       else:
#           raise ValueError(f"Unknown hazard type: {hazard.hazard_type}")
