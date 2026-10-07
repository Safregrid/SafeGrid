"""
Unit tests for SafeGrid Database layer.
Owner: Person 4 (Database & Offline System)

Tests isolation, schema creation, hazard persistence, risk result persistence,
and queries without affecting production database.
"""

import unittest
from datetime import datetime, timezone

from app.db.repository import (
    get_hazard,
    get_risk_result,
    init_db,
    list_hazards,
    list_hazards_with_risk,
    save_hazard,
    save_risk_result,
)
from app.db.session import Database
from app.models.hazard import GeoPoint, Hazard, RiskResult


class TestDatabaseRepository(unittest.TestCase):
    def setUp(self):
        """Run each test against a fresh, isolated in-memory database."""
        self.test_db = Database(db_path=":memory:")
        init_db(database=self.test_db)

    def test_save_and_get_hazard_dict(self):
        sample = {
            "id": "eq-test-01",
            "hazard_type": "earthquake",
            "source": "usgs",
            "timestamp": "2026-10-07T10:00:00Z",
            "latitude": 35.6762,
            "longitude": 139.6503,
            "raw_magnitude": 5.4,
            "raw_values": {"depth_km": 10.5}
        }
        saved = save_hazard(sample, database=self.test_db)
        self.assertEqual(saved["id"], "eq-test-01")
        self.assertEqual(saved["raw_magnitude"], 5.4)
        self.assertEqual(saved["raw_values"]["depth_km"], 10.5)

        retrieved = get_hazard("eq-test-01", database=self.test_db)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["id"], "eq-test-01")

    def test_save_and_get_hazard_pydantic_model(self):
        hazard_model = Hazard(
            id="eq-pydantic-02",
            hazard_type="earthquake",
            source="usgs",
            timestamp=datetime.now(timezone.utc),
            location=GeoPoint(coordinates=[139.6503, 35.6762]),
            raw_magnitude=6.8,
            raw_values={"depth_km": 25.0}
        )
        saved = save_hazard(hazard_model, database=self.test_db)
        self.assertEqual(saved["id"], "eq-pydantic-02")
        self.assertAlmostEqual(saved["longitude"], 139.6503)
        self.assertAlmostEqual(saved["latitude"], 35.6762)

    def test_save_and_get_risk_result(self):
        # First save the hazard
        sample = {
            "id": "eq-risk-01",
            "hazard_type": "earthquake",
            "source": "usgs",
            "timestamp": "2026-10-07T12:00:00Z",
            "latitude": 37.77,
            "longitude": -122.41,
            "raw_magnitude": 6.2
        }
        save_hazard(sample, database=self.test_db)

        # Now save RiskResult for it
        risk = RiskResult(
            hazard_id="eq-risk-01",
            risk_level="HIGH",
            severity_score=8.5,
            affected_area={"type": "Polygon", "coordinates": []},
            calculated_at=datetime.now(timezone.utc),
            notes="Magnitude > 6.0 in urban area"
        )
        saved_risk = save_risk_result(risk, database=self.test_db)
        self.assertEqual(saved_risk["risk_level"], "HIGH")
        self.assertEqual(saved_risk["severity_score"], 8.5)

        retrieved = get_risk_result("eq-risk-01", database=self.test_db)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["notes"], "Magnitude > 6.0 in urban area")

    def test_list_hazards_with_risk_join(self):
        # 1. Insert 2 hazards
        h1 = {
            "id": "h-1",
            "hazard_type": "earthquake",
            "source": "usgs",
            "timestamp": "2026-10-07T08:00:00Z",
            "latitude": 10.0,
            "longitude": 20.0
        }
        h2 = {
            "id": "h-2",
            "hazard_type": "earthquake",
            "source": "usgs",
            "timestamp": "2026-10-07T09:00:00Z",
            "latitude": 15.0,
            "longitude": 25.0
        }
        save_hazard(h1, database=self.test_db)
        save_hazard(h2, database=self.test_db)

        # 2. Add risk result to h2 only
        save_risk_result({
            "hazard_id": "h-2",
            "risk_level": "MODERATE",
            "severity_score": 5.0,
            "affected_area": {"type": "Circle"},
            "notes": "Moderate tremor"
        }, database=self.test_db)

        # 3. Query joined list
        joined = list_hazards_with_risk(database=self.test_db)
        self.assertEqual(len(joined), 2)
        # Most recent first: h-2
        self.assertEqual(joined[0]["id"], "h-2")
        self.assertEqual(joined[0]["risk_level"], "MODERATE")
        # h-1 has no risk yet
        self.assertEqual(joined[1]["id"], "h-1")
        self.assertIsNone(joined[1]["risk_level"])


if __name__ == "__main__":
    unittest.main()
