"""
Unit tests for Crop Observation Reminder API and Service.
"""

from datetime import date
import unittest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.farmer import Farmer
from app.models.farm import Farm
from app.models.crop import Crop
from app.models.crop_observation import CropObservation


class TestObservationReminders(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()

        # Create isolated test fixtures
        farmer = Farmer(name="Reminder Test Farmer", phone="9988776655")
        self.db.add(farmer)
        self.db.commit()
        self.db.refresh(farmer)
        self.farmer_id = farmer.id

        farm = Farm(
            farmer_id=farmer.id,
            name="Reminder Test Farm",
            location="19.9975, 73.7898",
            area=4.0,
            area_unit="acre",
        )
        self.db.add(farm)
        self.db.commit()
        self.db.refresh(farm)
        self.farm_id = farm.id

        crop = Crop(
            farm_id=farm.id,
            crop_name="Onion",
            variety="Garwa",
            sowing_date=date(2026, 7, 1),
            expected_harvest_date=date(2026, 11, 1),
            area=2.0,
            area_unit="acre",
        )
        self.db.add(crop)
        self.db.commit()
        self.db.refresh(crop)
        self.crop_id = crop.id

        # Add an observation to verify it remains unchanged
        obs = CropObservation(
            crop_id=crop.id,
            observation_date=date(2026, 8, 15),
            growth_stage="vegetative",
            health_status="healthy",
            notes="Initial healthy growth.",
        )
        self.db.add(obs)
        self.db.commit()
        self.db.refresh(obs)
        self.obs_id = obs.id

    def tearDown(self):
        # Clean up created farmer (cascades to farm, crop, reminder, observations)
        farmer = self.db.query(Farmer).filter(Farmer.id == self.farmer_id).first()
        if farmer:
            self.db.delete(farmer)
            self.db.commit()
        self.db.close()

    def test_1_create_reminder(self):
        """Test creating a new weekly observation reminder."""
        payload = {
            "enabled": True,
            "weekday": "sunday",
            "reminder_time": "08:00",
        }
        res = self.client.post(f"/api/v1/crops/{self.crop_id}/observation-reminder", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["crop_id"], self.crop_id)
        self.assertEqual(data["enabled"], True)
        self.assertEqual(data["weekday"], "sunday")
        self.assertEqual(data["reminder_time"], "08:00")

    def test_2_read_reminder(self):
        """Test reading an existing reminder."""
        # Create first
        self.client.post(
            f"/api/v1/crops/{self.crop_id}/observation-reminder",
            json={"enabled": True, "weekday": "monday", "reminder_time": "09:30"},
        )
        res = self.client.get(f"/api/v1/crops/{self.crop_id}/observation-reminder")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["weekday"], "monday")
        self.assertEqual(data["reminder_time"], "09:30")

    def test_3_update_reminder(self):
        """Test updating fields on an existing reminder."""
        self.client.post(
            f"/api/v1/crops/{self.crop_id}/observation-reminder",
            json={"enabled": True, "weekday": "sunday", "reminder_time": "08:00"},
        )
        res = self.client.put(
            f"/api/v1/crops/{self.crop_id}/observation-reminder",
            json={"weekday": "saturday", "reminder_time": "07:00"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["weekday"], "saturday")
        self.assertEqual(data["reminder_time"], "07:00")
        self.assertEqual(data["enabled"], True)

    def test_4_disable_reminder(self):
        """Test disabling an active reminder."""
        self.client.post(
            f"/api/v1/crops/{self.crop_id}/observation-reminder",
            json={"enabled": True, "weekday": "sunday", "reminder_time": "08:00"},
        )
        res = self.client.put(
            f"/api/v1/crops/{self.crop_id}/observation-reminder",
            json={"enabled": False},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["enabled"], False)

    def test_5_delete_reminder(self):
        """Test deleting a reminder."""
        self.client.post(
            f"/api/v1/crops/{self.crop_id}/observation-reminder",
            json={"enabled": True, "weekday": "friday", "reminder_time": "18:00"},
        )
        del_res = self.client.delete(f"/api/v1/crops/{self.crop_id}/observation-reminder")
        self.assertEqual(del_res.status_code, 204)

        get_res = self.client.get(f"/api/v1/crops/{self.crop_id}/observation-reminder")
        self.assertEqual(get_res.status_code, 404)

    def test_6_invalid_weekday(self):
        """Test rejection of invalid weekday string."""
        payload = {
            "enabled": True,
            "weekday": "funday",
            "reminder_time": "08:00",
        }
        res = self.client.post(f"/api/v1/crops/{self.crop_id}/observation-reminder", json=payload)
        self.assertEqual(res.status_code, 422)

    def test_7_invalid_time(self):
        """Test rejection of invalid time format."""
        payload = {
            "enabled": True,
            "weekday": "sunday",
            "reminder_time": "25:99",
        }
        res = self.client.post(f"/api/v1/crops/{self.crop_id}/observation-reminder", json=payload)
        self.assertEqual(res.status_code, 422)

    def test_8_invalid_crop(self):
        """Test 404 on nonexistent crop ID."""
        payload = {
            "enabled": True,
            "weekday": "sunday",
            "reminder_time": "08:00",
        }
        res = self.client.post("/api/v1/crops/999999/observation-reminder", json=payload)
        self.assertEqual(res.status_code, 404)

        get_res = self.client.get("/api/v1/crops/999999/observation-reminder")
        self.assertEqual(get_res.status_code, 404)

    def test_9_existing_observations_and_decision_engine_unaffected(self):
        """Verify that existing observations and decision assessment continue working unchanged."""
        # Create reminder
        self.client.post(
            f"/api/v1/crops/{self.crop_id}/observation-reminder",
            json={"enabled": True, "weekday": "wednesday", "reminder_time": "08:00"},
        )

        # Observations should still be intact
        obs_res = self.client.get(f"/api/v1/crops/{self.crop_id}/observations")
        self.assertEqual(obs_res.status_code, 200)
        self.assertEqual(len(obs_res.json()), 1)
        self.assertEqual(obs_res.json()[0]["growth_stage"], "vegetative")

        # Indicators should still work
        ind_res = self.client.get(f"/api/v1/crops/{self.crop_id}/indicators")
        self.assertEqual(ind_res.status_code, 200)

        # Decision assessment should still work
        dec_res = self.client.get(f"/api/v1/crops/{self.crop_id}/decision-assessment")
        self.assertEqual(dec_res.status_code, 200)


if __name__ == "__main__":
    unittest.main()
