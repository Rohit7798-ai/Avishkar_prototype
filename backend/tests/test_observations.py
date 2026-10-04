"""
Integration test suite for CropObservation, WeatherObservation, and MarketObservation APIs.
Verifies complete HTTP lifecycle, validation constraints, and relational cascades.
Uses an isolated in-memory test database with StaticPool and zero third-party testing dependencies.
"""

from datetime import date, datetime
import json
from sqlite3 import Connection as SQLite3Connection
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import uvicorn

from app.db.init_db import init_db
from app.db.session import get_db
from app.main import app
from app.models.base import Base


class TestObservationsApi(unittest.TestCase):
    """Verifies all observation endpoints, physical bounds validation, and cascades."""

    @classmethod
    def setUpClass(cls):
        # Configure dedicated isolated in-memory database with StaticPool
        cls.test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )

        @event.listens_for(cls.test_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            if isinstance(dbapi_connection, SQLite3Connection):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        init_db(target_engine=cls.test_engine)
        cls.TestingSessionLocal = sessionmaker(bind=cls.test_engine, expire_on_commit=False)

        def override_get_db():
            db = cls.TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db

        cls.port = 8789
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        config = uvicorn.Config(app, host="127.0.0.1", port=cls.port, log_level="error")
        cls.server = uvicorn.Server(config)
        cls.server_thread = threading.Thread(target=cls.server.run, daemon=True)
        cls.server_thread.start()
        time.sleep(0.6)

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=cls.test_engine)
        cls.test_engine.dispose()

    def setUp(self):
        # Clean and recreate tables between tests for complete isolation
        Base.metadata.drop_all(bind=self.test_engine)
        init_db(target_engine=self.test_engine)

    def _request(self, method: str, path: str, body: dict = None):
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json", "Accept": "application/json"} if body is not None else {"Accept": "application/json"}
        req = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(req) as response:
                status_code = response.getcode()
                raw = response.read()
                data = json.loads(raw.decode("utf-8")) if raw else None
                return status_code, data
        except HTTPError as e:
            raw = e.read()
            data = json.loads(raw.decode("utf-8")) if raw and raw.strip() else None
            return e.code, data

    def _create_sample_farmer_farm_crop(self):
        # Helper to set up parent hierarchy
        _, farmer = self._request("POST", "/api/v1/farmers", {"name": "Test Farmer"})
        _, farm = self._request("POST", "/api/v1/farms", {
            "farmer_id": farmer["id"],
            "name": "Niphad Farm",
            "location": "Nashik",
            "area": 5.0,
            "area_unit": "acre"
        })
        _, crop = self._request("POST", "/api/v1/crops", {
            "farm_id": farm["id"],
            "crop_name": "Onion",
            "variety": "Bhima Super",
            "sowing_date": "2026-07-01",
            "expected_harvest_date": "2026-10-30",
            "area": 2.5,
            "area_unit": "acre"
        })
        return farmer, farm, crop

    # =========================================================================
    # CROP OBSERVATION TESTS
    # =========================================================================

    def test_crop_observation_crud_lifecycle(self):
        _, farm, crop = self._create_sample_farmer_farm_crop()

        # 1. Create observation for valid crop
        payload = {
            "observation_date": "2026-08-15",
            "growth_stage": "vegetative",
            "health_status": "healthy",
            "notes": "Uniform vegetative growth observed, no thrips detected."
        }
        status_code, obs = self._request("POST", f"/api/v1/crops/{crop['id']}/observations", payload)
        self.assertEqual(status_code, 201)
        self.assertEqual(obs["crop_id"], crop["id"])
        self.assertEqual(obs["growth_stage"], "vegetative")
        self.assertEqual(obs["health_status"], "healthy")
        obs_id = obs["id"]

        # 2. Retrieve observations by crop
        status_code, observations = self._request("GET", f"/api/v1/crops/{crop['id']}/observations")
        self.assertEqual(status_code, 200)
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0]["id"], obs_id)

        # 3. Delete observation
        status_code, _ = self._request("DELETE", f"/api/v1/crop-observations/{obs_id}")
        self.assertEqual(status_code, 204)

        # 4. Verify gone
        status_code, observations_after = self._request("GET", f"/api/v1/crops/{crop['id']}/observations")
        self.assertEqual(status_code, 200)
        self.assertEqual(len(observations_after), 0)

    def test_reject_crop_observation_for_nonexistent_crop(self):
        payload = {
            "observation_date": "2026-08-15",
            "growth_stage": "flowering",
            "health_status": "healthy"
        }
        status_code, err = self._request("POST", "/api/v1/crops/99999/observations", payload)
        self.assertEqual(status_code, 404)
        self.assertIn("not found", err["detail"].lower())

    def test_crop_cascade_deletes_crop_observations(self):
        _, farm, crop = self._create_sample_farmer_farm_crop()

        # Add observation
        status_code, obs = self._request("POST", f"/api/v1/crops/{crop['id']}/observations", {
            "observation_date": "2026-08-20",
            "growth_stage": "fruiting",
            "health_status": "healthy"
        })
        self.assertEqual(status_code, 201)
        obs_id = obs["id"]

        # Delete parent crop
        status_code, _ = self._request("DELETE", f"/api/v1/crops/{crop['id']}")
        self.assertEqual(status_code, 204)

        # Deleting observation directly should now return 404 (already cascaded)
        status_code, _ = self._request("DELETE", f"/api/v1/crop-observations/{obs_id}")
        self.assertEqual(status_code, 404)

    # =========================================================================
    # WEATHER OBSERVATION TESTS
    # =========================================================================

    def test_weather_observation_crud_lifecycle(self):
        _, farm, _ = self._create_sample_farmer_farm_crop()

        # 1. Create valid weather observation
        payload = {
            "observed_at": "2026-08-15T08:30:00",
            "temperature": 27.5,
            "humidity": 65.0,
            "rainfall": 12.4,
            "wind_speed": 14.2
        }
        status_code, obs = self._request("POST", f"/api/v1/farms/{farm['id']}/weather-observations", payload)
        self.assertEqual(status_code, 201)
        self.assertEqual(obs["farm_id"], farm["id"])
        self.assertEqual(obs["temperature"], 27.5)
        self.assertEqual(obs["humidity"], 65.0)
        self.assertEqual(obs["rainfall"], 12.4)
        self.assertEqual(obs["wind_speed"], 14.2)
        obs_id = obs["id"]

        # 2. Retrieve weather observations by farm
        status_code, observations = self._request("GET", f"/api/v1/farms/{farm['id']}/weather-observations")
        self.assertEqual(status_code, 200)
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0]["id"], obs_id)

        # 3. Delete weather observation
        status_code, _ = self._request("DELETE", f"/api/v1/weather-observations/{obs_id}")
        self.assertEqual(status_code, 204)

        # 4. Verify gone
        status_code, observations_after = self._request("GET", f"/api/v1/farms/{farm['id']}/weather-observations")
        self.assertEqual(status_code, 200)
        self.assertEqual(len(observations_after), 0)

    def test_reject_weather_observation_for_nonexistent_farm(self):
        payload = {
            "observed_at": "2026-08-15T08:30:00",
            "temperature": 25.0,
            "humidity": 50.0,
            "rainfall": 0.0,
            "wind_speed": 10.0
        }
        status_code, err = self._request("POST", "/api/v1/farms/99999/weather-observations", payload)
        self.assertEqual(status_code, 404)
        self.assertIn("not found", err["detail"].lower())

    def test_reject_invalid_weather_measurements(self):
        _, farm, _ = self._create_sample_farmer_farm_crop()

        # Reject negative rainfall
        status_code, _ = self._request("POST", f"/api/v1/farms/{farm['id']}/weather-observations", {
            "observed_at": "2026-08-15T08:30:00",
            "temperature": 25.0,
            "humidity": 50.0,
            "rainfall": -5.0,
            "wind_speed": 10.0
        })
        self.assertIn(status_code, [400, 422])

        # Reject humidity > 100
        status_code, _ = self._request("POST", f"/api/v1/farms/{farm['id']}/weather-observations", {
            "observed_at": "2026-08-15T08:30:00",
            "temperature": 25.0,
            "humidity": 105.0,
            "rainfall": 0.0,
            "wind_speed": 10.0
        })
        self.assertIn(status_code, [400, 422])

        # Reject humidity < 0
        status_code, _ = self._request("POST", f"/api/v1/farms/{farm['id']}/weather-observations", {
            "observed_at": "2026-08-15T08:30:00",
            "temperature": 25.0,
            "humidity": -2.0,
            "rainfall": 0.0,
            "wind_speed": 10.0
        })
        self.assertIn(status_code, [400, 422])

        # Reject negative wind speed
        status_code, _ = self._request("POST", f"/api/v1/farms/{farm['id']}/weather-observations", {
            "observed_at": "2026-08-15T08:30:00",
            "temperature": 25.0,
            "humidity": 50.0,
            "rainfall": 0.0,
            "wind_speed": -1.5
        })
        self.assertIn(status_code, [400, 422])

    def test_farm_cascade_deletes_weather_observations(self):
        _, farm, _ = self._create_sample_farmer_farm_crop()

        status_code, obs = self._request("POST", f"/api/v1/farms/{farm['id']}/weather-observations", {
            "observed_at": "2026-08-15T08:30:00",
            "temperature": 25.0,
            "humidity": 50.0,
            "rainfall": 0.0,
            "wind_speed": 10.0
        })
        self.assertEqual(status_code, 201)
        obs_id = obs["id"]

        # Delete parent farm
        status_code, _ = self._request("DELETE", f"/api/v1/farms/{farm['id']}")
        self.assertEqual(status_code, 204)

        # Deleting observation directly should now return 404 (already cascaded)
        status_code, _ = self._request("DELETE", f"/api/v1/weather-observations/{obs_id}")
        self.assertEqual(status_code, 404)

    # =========================================================================
    # MARKET OBSERVATION TESTS
    # =========================================================================

    def test_market_observation_crud_lifecycle(self):
        # 1. Create valid market observation
        payload = {
            "crop_name": "Onion",
            "market_name": "Lasalgaon APMC",
            "observed_date": "2026-08-15",
            "price": 1850.0,
            "unit": "Rs/Quintal"
        }
        status_code, obs = self._request("POST", "/api/v1/market-observations", payload)
        self.assertEqual(status_code, 201)
        self.assertEqual(obs["crop_name"], "Onion")
        self.assertEqual(obs["market_name"], "Lasalgaon APMC")
        self.assertEqual(obs["price"], 1850.0)
        self.assertEqual(obs["unit"], "Rs/Quintal")
        obs_id = obs["id"]

        # 2. Retrieve all market observations
        status_code, observations = self._request("GET", "/api/v1/market-observations")
        self.assertEqual(status_code, 200)
        self.assertGreaterEqual(len(observations), 1)

        # 3. Filter by crop_name
        status_code, filtered = self._request("GET", "/api/v1/market-observations?crop_name=Onion")
        self.assertEqual(status_code, 200)
        self.assertEqual(filtered[0]["crop_name"], "Onion")

        # 4. Delete market observation
        status_code, _ = self._request("DELETE", f"/api/v1/market-observations/{obs_id}")
        self.assertEqual(status_code, 204)

        # 5. Verify gone
        status_code, err = self._request("DELETE", f"/api/v1/market-observations/{obs_id}")
        self.assertEqual(status_code, 404)

    def test_reject_invalid_market_price(self):
        # Reject price <= 0
        status_code, _ = self._request("POST", "/api/v1/market-observations", {
            "crop_name": "Onion",
            "market_name": "Pimpalgaon APMC",
            "observed_date": "2026-08-15",
            "price": 0.0,
            "unit": "Rs/Quintal"
        })
        self.assertIn(status_code, [400, 422])

        status_code, _ = self._request("POST", "/api/v1/market-observations", {
            "crop_name": "Onion",
            "market_name": "Pimpalgaon APMC",
            "observed_date": "2026-08-15",
            "price": -100.0,
            "unit": "Rs/Quintal"
        })
        self.assertIn(status_code, [400, 422])

    def test_market_observation_independence(self):
        _, farm, crop = self._create_sample_farmer_farm_crop()

        # Create market observation
        status_code, obs = self._request("POST", "/api/v1/market-observations", {
            "crop_name": "Onion",
            "market_name": "Yeola APMC",
            "observed_date": "2026-08-16",
            "price": 1920.0,
            "unit": "Rs/Quintal"
        })
        self.assertEqual(status_code, 201)
        obs_id = obs["id"]

        # Delete farm and crop
        self._request("DELETE", f"/api/v1/farms/{farm['id']}")

        # Market observation MUST still exist and remain queryable
        status_code, observations = self._request("GET", "/api/v1/market-observations")
        self.assertEqual(status_code, 200)
        found = any(item["id"] == obs_id for item in observations)
        self.assertTrue(found, "Market observation must not be deleted when a farm is deleted")


if __name__ == "__main__":
    unittest.main()
