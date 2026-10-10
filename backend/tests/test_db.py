"""
Unit tests for SafeGrid Database layer.
Owner: Person 4 (Database & Offline System)

Updated 2026-10-07: Aligned with agreed Hazard model fields.
Tests both earthquake-type and rainfall-type hazards to confirm
the repository is generic and not earthquake-specific.
"""

import unittest
from datetime import datetime, timezone

from app.db.repository import (
    get_data_record,
    get_hazard,
    get_risk_result,
    init_db,
    list_data_records,
    list_hazards,
    list_hazards_with_risk,
    save_data_record,
    save_hazard,
    save_risk_result,
)
from app.db.session import Database
from app.models.data import DataRecord
from app.models.hazard import GeoPoint, Hazard, RiskResult


class TestDatabaseRepository(unittest.TestCase):
    def setUp(self):
        """Run each test in a fresh in-memory database. Never touches safegrid.db."""
        self.test_db = Database(db_path=":memory:")
        init_db(database=self.test_db)

    # ------------------------------------------------------------------
    # Test 0: Save and retrieve a provider DataRecord
    # ------------------------------------------------------------------
    def test_save_and_retrieve_data_record(self):
        record = DataRecord(
            id="open-meteo:12.9:77.5:2026-10-09T10:00",
            data_type="weather",
            source="open_meteo",
            timestamp=datetime.now(timezone.utc),
            location=GeoPoint(coordinates=[77.5, 12.9]),
            magnitude=0.0,
            probability=10.0,
            specific_data={"precipitation_mm": 0.0, "wind_speed_kmh": 5.2},
        )
        saved = save_data_record(record, database=self.test_db)
        self.assertEqual(saved["id"], record.id)
        self.assertEqual(saved["data_type"], "weather")
        self.assertEqual(saved["source"], "open_meteo")
        self.assertEqual(saved["specific_data"]["wind_speed_kmh"], 5.2)

        fetched = get_data_record(record.id, database=self.test_db)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["source"], "open_meteo")

        records_list = list_data_records(database=self.test_db)
        self.assertEqual(len(records_list), 1)

    # ------------------------------------------------------------------
    # Test 1: Save and retrieve an EARTHQUAKE hazard using plain dict
    # ------------------------------------------------------------------
    def test_save_earthquake_as_dict(self):
        sample = {
            "id": "eq-usgs-001",
            "hazard_type": "earthquake",
            "source": "usgs",
            "timestamp": "2026-10-07T10:00:00Z",
            "latitude": 35.6762,
            "longitude": 139.6503,
            "magnitude": 5.4,
            "probability": None,
            "specific_data": {"depth_km": 10.5, "felt_reports": 340}
        }
        saved = save_hazard(sample, database=self.test_db)
        self.assertEqual(saved["id"], "eq-usgs-001")
        self.assertEqual(saved["magnitude"], 5.4)
        self.assertIsNone(saved["probability"])
        self.assertEqual(saved["specific_data"]["depth_km"], 10.5)

    # ------------------------------------------------------------------
    # Test 2: Save and retrieve a RAINFALL hazard using Pydantic model
    # ------------------------------------------------------------------
    def test_save_rainfall_as_pydantic_model(self):
        rainfall_hazard = Hazard(
            id="rain-openmeteo-001",
            hazard_type="rainfall",
            source="open_meteo",
            timestamp=datetime.now(timezone.utc),
            location=GeoPoint(coordinates=[72.8777, 19.0760]),  # Mumbai [lon, lat]
            magnitude=None,          # Not applicable for rainfall
            probability=0.87,        # 87% probability of heavy rain
            specific_data={"precipitation_mm": 95.4, "intensity": "heavy"}
        )
        saved = save_hazard(rainfall_hazard, database=self.test_db)
        self.assertEqual(saved["id"], "rain-openmeteo-001")
        self.assertEqual(saved["hazard_type"], "rainfall")
        self.assertIsNone(saved["magnitude"])
        self.assertAlmostEqual(saved["probability"], 0.87)
        self.assertEqual(saved["specific_data"]["intensity"], "heavy")
        # Coordinates extracted from GeoPoint correctly
        self.assertAlmostEqual(saved["longitude"], 72.8777)
        self.assertAlmostEqual(saved["latitude"], 19.0760)

    # ------------------------------------------------------------------
    # Test 3: Save a RiskResult and link it to a hazard
    # ------------------------------------------------------------------
    def test_save_and_retrieve_risk_result(self):
        # First: save the hazard
        save_hazard({
            "id": "eq-risk-test-01",
            "hazard_type": "earthquake",
            "source": "usgs",
            "timestamp": "2026-10-07T12:00:00Z",
            "latitude": 37.77,
            "longitude": -122.41,
            "magnitude": 6.5,
        }, database=self.test_db)

        # Then: save the risk result (from Person 2)
        risk = RiskResult(
            hazard_id="eq-risk-test-01",
            risk_level="HIGH",
            severity_score=8.5,
            affected_area={"type": "Polygon", "coordinates": []},
            calculated_at=datetime.now(timezone.utc),
            notes="Magnitude > 6.0 in urban area"
        )
        saved_risk = save_risk_result(risk, database=self.test_db)
        self.assertEqual(saved_risk["risk_level"], "HIGH")
        self.assertEqual(saved_risk["severity_score"], 8.5)

        retrieved = get_risk_result("eq-risk-test-01", database=self.test_db)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["notes"], "Magnitude > 6.0 in urban area")

    # ------------------------------------------------------------------
    # Test 4: list_hazards_with_risk returns correct joined structure
    #         for Person 3's map — with both an earthquake and rainfall entry
    # ------------------------------------------------------------------
    def test_list_hazards_with_risk_join_mixed_types(self):
        # Save an earthquake with risk result
        save_hazard({
            "id": "eq-join-01",
            "hazard_type": "earthquake",
            "source": "usgs",
            "timestamp": "2026-10-07T08:00:00Z",
            "latitude": 10.0,
            "longitude": 20.0,
            "magnitude": 6.1,
        }, database=self.test_db)
        save_risk_result({
            "hazard_id": "eq-join-01",
            "risk_level": "HIGH",
            "severity_score": 7.5,
            "affected_area": {"type": "Polygon"},
            "notes": "Severe shaking expected"
        }, database=self.test_db)

        # Save a rainfall hazard WITHOUT a risk result yet (still pending Person 2)
        save_hazard({
            "id": "rain-join-02",
            "hazard_type": "rainfall",
            "source": "open_meteo",
            "timestamp": "2026-10-07T09:00:00Z",
            "latitude": 19.0,
            "longitude": 72.8,
            "probability": 0.75,
        }, database=self.test_db)

        joined = list_hazards_with_risk(database=self.test_db)
        self.assertEqual(len(joined), 2)

        # Most recent first (rainfall at 09:00 comes first)
        rain = joined[0]
        quake = joined[1]

        self.assertEqual(rain["id"], "rain-join-02")
        self.assertEqual(rain["hazard_type"], "rainfall")
        # Rainfall has no risk result yet — all risk fields should be None
        self.assertIsNone(rain["risk_level"])
        self.assertIsNone(rain["affected_area"])

        self.assertEqual(quake["id"], "eq-join-01")
        self.assertEqual(quake["risk_level"], "HIGH")
        self.assertIsNotNone(quake["affected_area"])

        # Confirm all keys Person 3's map needs are present
        required_keys = {
            "id", "hazard_type", "source", "timestamp",
            "latitude", "longitude", "magnitude", "probability",
            "specific_data", "risk_level",
            "severity_score", "affected_area", "notes"
        }
        self.assertTrue(required_keys.issubset(set(joined[0].keys())))

    def test_resaving_hazard_keeps_risk_result(self):
        hazard = {
            "id": "eq-10",
            "hazard_type": "earthquake",
            "source": "usgs",
            "timestamp": "2026-10-07T10:00:00Z",
            "latitude": 35.6,
            "longitude": 139.6,
            "magnitude": 5.0,
        }

        # 1. Save the hazard, then give it a rating
        save_hazard(hazard, database=self.test_db)
        save_risk_result(
            {
                "hazard_id": "eq-10",
                "risk_level": "HIGH",
                "severity_score": 8.0,
                "affected_area": {},
            },
            database=self.test_db,
        )

        # 2. Save the SAME hazard again (like USGS sending a correction)
        hazard["magnitude"] = 5.4
        save_hazard(hazard, database=self.test_db)

        # 3. The rating must still exist
        risk = get_risk_result("eq-10", database=self.test_db)
        self.assertIsNotNone(risk)
        self.assertEqual(risk["risk_level"], "HIGH")


if __name__ == "__main__":
    unittest.main()
