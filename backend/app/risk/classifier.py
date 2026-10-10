"""
Risk classifier engine for SafeGrid.
Owner: Person 2 (Risk Engine & Geospatial Processing)
Branch: feature/risk-engine

Accepts a Hazard object (from Person 1's ingestion layer), evaluates hazard-specific
rules (precipitation from rain.py), and returns a RiskResult object.
"""

from __future__ import annotations

from datetime import datetime
from app.models.hazard import Hazard, RiskResult
from app.risk import rain


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
        # TODO: Person 2 will create a separate file for earthquakes etc.
        raise NotImplementedError(f"Classification for hazard type '{hazard.hazard_type}' will be added in a separate module.")
