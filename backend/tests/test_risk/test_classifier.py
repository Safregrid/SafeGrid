"""
Risk engine unit test stubs.

Person 2 owns this file.
Write tests here for every risk classification rule.
Tests must run without network access (use only local/mock data).

Brain requirement: "Critical risk calculations should have automated tests."
"""

# TODO (Person 2): add unit tests for classifier.py
# TODO (Person 2): add unit tests for geometry.py
#
# Example structure:
#
#   from app.risk.classifier import classify
#   from app.models.hazard import Hazard, GeoPoint
#   from datetime import datetime, timezone
#
#   def make_earthquake(magnitude: float) -> Hazard:
#       return Hazard(
#           id="test-eq-1",
#           hazard_type="earthquake",
#           source="usgs",
#           timestamp=datetime.now(tz=timezone.utc),
#           location=GeoPoint(coordinates=[0.0, 0.0]),
#           raw_magnitude=magnitude,
#       )
#
#   def test_high_magnitude_is_high_risk():
#       result = classify(make_earthquake(7.0))
#       assert result.risk_level == "HIGH"
