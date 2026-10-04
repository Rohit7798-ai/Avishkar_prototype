"""
Integration test suite for Agricultural Decision-Ready Indicators.
Verifies deterministic calculations for Crop, Farm Weather, and Market indicators,
ensuring zero database mutations, proper edge-case handling, and strict read-only behavior.
"""

from datetime import date, datetime, timedelta
import json
from sqlite3 import Connection as SQLite3Connection
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import uvicorn

from app.db.init_db import init_db
from app.db.session import get_db
from app.main import app
from app.models.base import Base


class TestIndicatorsApi(unittest.TestCase):
    """Verifies all indicator endpoints, statistical calculations, and immutability."""

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

        cls.port = 8792
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

    def _setup_farmer_farm_crop(self):
        _, farmer = self._request("POST", "/api/v1/farmers", {"name": "Suresh Patil"})
        _, farm = self._request("POST", "/api/v1/farms", {
            "farmer_id": farmer["id"],
            "name": "Niphad Onion Field",
            "location": "Niphad, Nashik",
            "area": 5.0,
            "area_unit": "acre",
        })
        _, crop = self._request("POST", "/api/v1/crops", {
            "farm_id": farm["id"],
            "crop_name": "Onion",
            "variety": "Bhima Dark Red",
            "sowing_date": "2026-06-15",
            "expected_harvest_date": "2026-10-15",
            "area": 3.0,
            "area_unit": "acre",
        })
        return farmer, farm, crop

    # =========================================================================
    # CROP INDICATORS TESTS
    # =========================================================================

    def test_crop_indicators_not_found(self):
        code, data = self._request("GET", "/api/v1/crops/9999/indicators")
        self.assertEqual(code, 404)
        self.assertIn("detail", data)

    def test_crop_indicators_no_observations(self):
        _, _, crop = self._setup_farmer_farm_crop()
        code, data = self._request("GET", f"/api/v1/crops/{crop['id']}/indicators")
        self.assertEqual(code, 200)
        self.assertEqual(data["crop_id"], crop["id"])
        self.assertEqual(data["observation_count"], 0)
        self.assertEqual(data["number_of_observations"], 0)
        self.assertIsNone(data["latest_growth_stage"])
        self.assertIsNone(data["latest_health_status"])
        self.assertIsNone(data["latest_observation_date"])
        self.assertIsNone(data["days_since_latest_observation"])

    def test_crop_indicators_one_observation(self):
        _, _, crop = self._setup_farmer_farm_crop()
        obs_date = (date.today() - timedelta(days=4)).isoformat()
        code, _ = self._request("POST", f"/api/v1/crops/{crop['id']}/observations", {
            "observation_date": obs_date,
            "growth_stage": "vegetative",
            "health_status": "healthy",
            "notes": "Good foliage development",
        })
        self.assertEqual(code, 201)

        code, data = self._request("GET", f"/api/v1/crops/{crop['id']}/indicators")
        self.assertEqual(code, 200)
        self.assertEqual(data["crop_id"], crop["id"])
        self.assertEqual(data["observation_count"], 1)
        self.assertEqual(data["latest_growth_stage"], "vegetative")
        self.assertEqual(data["latest_health_status"], "healthy")
        self.assertEqual(data["latest_observation_date"], obs_date)
        self.assertEqual(data["days_since_latest_observation"], 4)

    def test_crop_indicators_multiple_observations_latest_selection(self):
        _, _, crop = self._setup_farmer_farm_crop()
        d1 = (date.today() - timedelta(days=20)).isoformat()
        d2 = (date.today() - timedelta(days=10)).isoformat()
        d3 = (date.today() - timedelta(days=2)).isoformat()

        # Insert out of order
        self._request("POST", f"/api/v1/crops/{crop['id']}/observations", {
            "observation_date": d2,
            "growth_stage": "fruiting",
            "health_status": "moderate",
        })
        self._request("POST", f"/api/v1/crops/{crop['id']}/observations", {
            "observation_date": d1,
            "growth_stage": "vegetative",
            "health_status": "healthy",
        })
        self._request("POST", f"/api/v1/crops/{crop['id']}/observations", {
            "observation_date": d3,
            "growth_stage": "maturity",
            "health_status": "healthy",
        })

        code, data = self._request("GET", f"/api/v1/crops/{crop['id']}/indicators")
        self.assertEqual(code, 200)
        self.assertEqual(data["observation_count"], 3)
        self.assertEqual(data["number_of_observations"], 3)
        self.assertEqual(data["latest_growth_stage"], "maturity")
        self.assertEqual(data["latest_health_status"], "healthy")
        self.assertEqual(data["latest_observation_date"], d3)
        self.assertEqual(data["days_since_latest_observation"], 2)

    # =========================================================================
    # WEATHER INDICATORS TESTS
    # =========================================================================

    def test_weather_indicators_not_found(self):
        code, data = self._request("GET", "/api/v1/farms/9999/weather-indicators")
        self.assertEqual(code, 404)
        self.assertIn("detail", data)

    def test_weather_indicators_no_observations(self):
        _, farm, _ = self._setup_farmer_farm_crop()
        code, data = self._request("GET", f"/api/v1/farms/{farm['id']}/weather-indicators")
        self.assertEqual(code, 200)
        self.assertEqual(data["farm_id"], farm["id"])
        self.assertEqual(data["observation_count"], 0)
        self.assertEqual(data["number_of_observations"], 0)
        self.assertIsNone(data["latest_temperature"])
        self.assertIsNone(data["latest_humidity"])
        self.assertIsNone(data["latest_rainfall"])
        self.assertIsNone(data["latest_wind_speed"])
        self.assertIsNone(data["latest_observed_at"])
        self.assertIsNone(data["average_temperature"])
        self.assertIsNone(data["total_rainfall"])
        self.assertIsNone(data["average_humidity"])
        self.assertIsNone(data["average_wind_speed"])

    def test_weather_indicators_one_observation(self):
        _, farm, _ = self._setup_farmer_farm_crop()
        t = "2026-10-01T10:00:00"
        self._request("POST", f"/api/v1/farms/{farm['id']}/weather-observations", {
            "observed_at": t,
            "temperature": 28.0,
            "humidity": 65.0,
            "rainfall": 5.0,
            "wind_speed": 12.0,
        })

        code, data = self._request("GET", f"/api/v1/farms/{farm['id']}/weather-indicators")
        self.assertEqual(code, 200)
        self.assertEqual(data["farm_id"], farm["id"])
        self.assertEqual(data["observation_count"], 1)
        self.assertEqual(data["latest_temperature"], 28.0)
        self.assertEqual(data["latest_humidity"], 65.0)
        self.assertEqual(data["latest_rainfall"], 5.0)
        self.assertEqual(data["latest_wind_speed"], 12.0)
        self.assertEqual(data["average_temperature"], 28.0)
        self.assertEqual(data["total_rainfall"], 5.0)
        self.assertEqual(data["average_humidity"], 65.0)
        self.assertEqual(data["average_wind_speed"], 12.0)

    def test_weather_indicators_multiple_observations_stats_and_latest(self):
        _, farm, _ = self._setup_farmer_farm_crop()
        # Obs 1: earlier
        self._request("POST", f"/api/v1/farms/{farm['id']}/weather-observations", {
            "observed_at": "2026-10-01T08:00:00",
            "temperature": 20.0,
            "humidity": 80.0,
            "rainfall": 10.5,
            "wind_speed": 5.0,
        })
        # Obs 2: latest
        self._request("POST", f"/api/v1/farms/{farm['id']}/weather-observations", {
            "observed_at": "2026-10-01T14:00:00",
            "temperature": 32.0,
            "humidity": 40.0,
            "rainfall": 0.0,
            "wind_speed": 15.0,
        })
        # Obs 3: middle
        self._request("POST", f"/api/v1/farms/{farm['id']}/weather-observations", {
            "observed_at": "2026-10-01T11:00:00",
            "temperature": 26.0,
            "humidity": 60.0,
            "rainfall": 2.5,
            "wind_speed": 10.0,
        })

        code, data = self._request("GET", f"/api/v1/farms/{farm['id']}/weather-indicators")
        self.assertEqual(code, 200)
        self.assertEqual(data["observation_count"], 3)
        # Latest should be 14:00:00
        self.assertIn("2026-10-01T14:00:00", data["latest_observed_at"])
        self.assertEqual(data["latest_temperature"], 32.0)
        self.assertEqual(data["latest_humidity"], 40.0)
        self.assertEqual(data["latest_rainfall"], 0.0)
        self.assertEqual(data["latest_wind_speed"], 15.0)

        # Averages: (20 + 32 + 26) / 3 = 78 / 3 = 26.0
        self.assertEqual(data["average_temperature"], 26.0)
        # Total rainfall: 10.5 + 0.0 + 2.5 = 13.0
        self.assertEqual(data["total_rainfall"], 13.0)
        # Avg humidity: (80 + 40 + 60) / 3 = 180 / 3 = 60.0
        self.assertEqual(data["average_humidity"], 60.0)
        # Avg wind speed: (5 + 15 + 10) / 3 = 30 / 3 = 10.0
        self.assertEqual(data["average_wind_speed"], 10.0)

    # =========================================================================
    # MARKET INDICATORS TESTS
    # =========================================================================

    def test_market_indicators_no_observations(self):
        code, data = self._request("GET", "/api/v1/market-indicators?crop_name=Onion&market_name=Lasalgaon")
        self.assertEqual(code, 200)
        self.assertEqual(data["observation_count"], 0)
        self.assertEqual(data["number_of_observations"], 0)
        self.assertEqual(data["crop_name"], "Onion")
        self.assertEqual(data["market_name"], "Lasalgaon")
        self.assertIsNone(data["latest_price"])
        self.assertIsNone(data["earliest_price"])
        self.assertIsNone(data["highest_price"])
        self.assertIsNone(data["lowest_price"])
        self.assertIsNone(data["average_price"])
        self.assertIsNone(data["latest_observation_date"])
        self.assertIsNone(data["price_change"])
        self.assertIsNone(data["price_change_percentage"])

    def test_market_indicators_one_observation(self):
        self._request("POST", "/api/v1/market-observations", {
            "crop_name": "Onion",
            "market_name": "Lasalgaon APMC",
            "observed_date": "2026-10-01",
            "price": 2000.0,
            "unit": "Rs/Quintal",
        })

        code, data = self._request("GET", "/api/v1/market-indicators?crop_name=Onion")
        self.assertEqual(code, 200)
        self.assertEqual(data["observation_count"], 1)
        self.assertEqual(data["latest_price"], 2000.0)
        self.assertEqual(data["earliest_price"], 2000.0)
        self.assertEqual(data["highest_price"], 2000.0)
        self.assertEqual(data["lowest_price"], 2000.0)
        self.assertEqual(data["average_price"], 2000.0)
        self.assertEqual(data["latest_observation_date"], "2026-10-01")
        # Single observation: change is 0.0, percentage is None
        self.assertEqual(data["price_change"], 0.0)
        self.assertIsNone(data["price_change_percentage"])

    def test_market_indicators_multiple_observations_stats_and_change(self):
        # 3 observations over time: 1800 -> 2200 -> 2100
        self._request("POST", "/api/v1/market-observations", {
            "crop_name": "Onion",
            "market_name": "Lasalgaon APMC",
            "observed_date": "2026-09-20",
            "price": 1800.0,
            "unit": "Rs/Quintal",
        })
        self._request("POST", "/api/v1/market-observations", {
            "crop_name": "Onion",
            "market_name": "Lasalgaon APMC",
            "observed_date": "2026-09-25",
            "price": 2200.0,
            "unit": "Rs/Quintal",
        })
        self._request("POST", "/api/v1/market-observations", {
            "crop_name": "Onion",
            "market_name": "Lasalgaon APMC",
            "observed_date": "2026-10-02",
            "price": 2070.0,
            "unit": "Rs/Quintal",
        })

        code, data = self._request("GET", "/api/v1/market-indicators?crop_name=Onion&market_name=Lasalgaon%20APMC")
        self.assertEqual(code, 200)
        self.assertEqual(data["observation_count"], 3)
        self.assertEqual(data["earliest_price"], 1800.0)
        self.assertEqual(data["latest_price"], 2070.0)
        self.assertEqual(data["highest_price"], 2200.0)
        self.assertEqual(data["lowest_price"], 1800.0)
        # Average: (1800 + 2200 + 2070) / 3 = 6070 / 3 = 2023.33
        self.assertEqual(data["average_price"], 2023.33)
        self.assertEqual(data["latest_observation_date"], "2026-10-02")
        # Change: 2070 - 1800 = +270.0
        self.assertEqual(data["price_change"], 270.0)
        # Percentage change: (270 / 1800) * 100 = 15.0%
        self.assertEqual(data["price_change_percentage"], 15.0)

    def test_market_indicators_negative_price_change(self):
        # Price drops from 2000.0 down to 1500.0
        self._request("POST", "/api/v1/market-observations", {
            "crop_name": "Potato",
            "market_name": "Pune APMC",
            "observed_date": "2026-09-10",
            "price": 2000.0,
            "unit": "Rs/Quintal",
        })
        self._request("POST", "/api/v1/market-observations", {
            "crop_name": "Potato",
            "market_name": "Pune APMC",
            "observed_date": "2026-09-20",
            "price": 1500.0,
            "unit": "Rs/Quintal",
        })

        code, data = self._request("GET", "/api/v1/market-indicators?crop_name=Potato")
        self.assertEqual(code, 200)
        self.assertEqual(data["price_change"], -500.0)
        # (-500 / 2000) * 100 = -25.0%
        self.assertEqual(data["price_change_percentage"], -25.0)

    # =========================================================================
    # IMMUTABILITY TEST (Endpoints must not modify database records)
    # =========================================================================

    def test_indicator_endpoints_do_not_modify_database(self):
        _, farm, crop = self._setup_farmer_farm_crop()
        self._request("POST", f"/api/v1/crops/{crop['id']}/observations", {
            "observation_date": "2026-10-01",
            "growth_stage": "vegetative",
            "health_status": "healthy",
        })
        self._request("POST", f"/api/v1/farms/{farm['id']}/weather-observations", {
            "observed_at": "2026-10-01T12:00:00",
            "temperature": 25.0,
            "humidity": 60.0,
            "rainfall": 0.0,
            "wind_speed": 10.0,
        })
        self._request("POST", "/api/v1/market-observations", {
            "crop_name": "Onion",
            "market_name": "Nashik APMC",
            "observed_date": "2026-10-01",
            "price": 1900.0,
            "unit": "Rs/Quintal",
        })

        # Count records in all tables before calling GET indicator endpoints
        tables = ["farmers", "farms", "crops", "crop_observations", "weather_observations", "market_observations"]
        counts_before = {}
        with self.TestingSessionLocal() as session:
            for t in tables:
                counts_before[t] = session.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()

        # Call all indicator endpoints repeatedly
        self._request("GET", f"/api/v1/crops/{crop['id']}/indicators")
        self._request("GET", f"/api/v1/farms/{farm['id']}/weather-indicators")
        self._request("GET", "/api/v1/market-indicators?crop_name=Onion")
        self._request("GET", "/api/v1/market-indicators")

        # Verify record counts are completely unchanged
        counts_after = {}
        with self.TestingSessionLocal() as session:
            for t in tables:
                counts_after[t] = session.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()

        self.assertEqual(counts_before, counts_after)


if __name__ == "__main__":
    unittest.main()
