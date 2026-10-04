"""
Integration test suite for Transparent Agricultural Decision Engine.
Verifies deterministic rule-based assessments for harvest and market conditions.
Ensures explainable decision factors, strict data sufficiency handling,
and read-only database immutability with zero ML/AI dependencies.
"""

from datetime import date, timedelta
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


class TestDecisionEngineApi(unittest.TestCase):
    """Verifies all harvest and market decision assessment rules and safety guarantees."""

    @classmethod
    def setUpClass(cls):
        # Dedicated isolated in-memory test database
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

        cls.port = 8794
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
        _, farmer = self._request("POST", "/api/v1/farmers", {"name": "Vitthalrao Kadam"})
        _, farm = self._request("POST", "/api/v1/farms", {
            "farmer_id": farmer["id"],
            "name": "Pimpalgaon Parcel",
            "location": "Pimpalgaon Baswant, Nashik",
            "area": 4.5,
            "area_unit": "acre",
        })
        _, crop = self._request("POST", "/api/v1/crops", {
            "farm_id": farm["id"],
            "crop_name": "Onion",
            "variety": "Phule Samarth",
            "sowing_date": "2026-06-20",
            "expected_harvest_date": "2026-10-25",
            "area": 3.0,
            "area_unit": "acre",
        })
        return farmer, farm, crop

    # =========================================================================
    # HARVEST ASSESSMENT TESTS
    # =========================================================================

    def test_harvest_assessment_crop_not_found(self):
        code, data = self._request("GET", "/api/v1/crops/9999/decision-assessment")
        self.assertEqual(code, 404)
        self.assertIn("detail", data)

    def test_harvest_assessment_no_crop_observations(self):
        _, _, crop = self._setup_farmer_farm_crop()
        code, data = self._request("GET", f"/api/v1/crops/{crop['id']}/decision-assessment")
        self.assertEqual(code, 200)
        self.assertEqual(data["crop_id"], crop["id"])
        self.assertEqual(data["status"], "insufficient_data")
        self.assertEqual(data["data_sufficiency"], "insufficient")
        self.assertTrue(len(data["factors"]) >= 1)
        self.assertEqual(data["factors"][0]["name"], "crop_observations")
        self.assertIn("No field observations", data["factors"][0]["observation"])

    def test_harvest_assessment_early_stage(self):
        _, farm, crop = self._setup_farmer_farm_crop()
        self._request("POST", f"/api/v1/crops/{crop['id']}/observations", {
            "observation_date": date.today().isoformat(),
            "growth_stage": "early",
            "health_status": "healthy",
        })
        code, data = self._request("GET", f"/api/v1/crops/{crop['id']}/decision-assessment")
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "not_ready")
        self.assertEqual(data["data_sufficiency"], "partial")  # No weather observations yet
        stage_factor = next(f for f in data["factors"] if f["name"] == "growth_stage")
        self.assertEqual(stage_factor["value"], "early")

    def test_harvest_assessment_vegetative_stage(self):
        _, farm, crop = self._setup_farmer_farm_crop()
        self._request("POST", f"/api/v1/crops/{crop['id']}/observations", {
            "observation_date": date.today().isoformat(),
            "growth_stage": "vegetative",
            "health_status": "healthy",
        })
        code, data = self._request("GET", f"/api/v1/crops/{crop['id']}/decision-assessment")
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "not_ready")

    def test_harvest_assessment_flowering_stage(self):
        _, farm, crop = self._setup_farmer_farm_crop()
        self._request("POST", f"/api/v1/crops/{crop['id']}/observations", {
            "observation_date": date.today().isoformat(),
            "growth_stage": "flowering",
            "health_status": "moderate",
        })
        code, data = self._request("GET", f"/api/v1/crops/{crop['id']}/decision-assessment")
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "not_ready")

    def test_harvest_assessment_fruiting_stage(self):
        _, farm, crop = self._setup_farmer_farm_crop()
        self._request("POST", f"/api/v1/crops/{crop['id']}/observations", {
            "observation_date": date.today().isoformat(),
            "growth_stage": "fruiting",
            "health_status": "healthy",
        })
        code, data = self._request("GET", f"/api/v1/crops/{crop['id']}/decision-assessment")
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "approaching")

    def test_harvest_assessment_maturity_stage(self):
        _, farm, crop = self._setup_farmer_farm_crop()
        self._request("POST", f"/api/v1/crops/{crop['id']}/observations", {
            "observation_date": date.today().isoformat(),
            "growth_stage": "maturity",
            "health_status": "healthy",
        })
        code, data = self._request("GET", f"/api/v1/crops/{crop['id']}/decision-assessment")
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "maturity_observed")

    def test_harvest_assessment_post_maturity_stage(self):
        _, farm, crop = self._setup_farmer_farm_crop()
        self._request("POST", f"/api/v1/crops/{crop['id']}/observations", {
            "observation_date": date.today().isoformat(),
            "growth_stage": "post_maturity",
            "health_status": "healthy",
        })
        code, data = self._request("GET", f"/api/v1/crops/{crop['id']}/decision-assessment")
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "maturity_observed")

    def test_harvest_assessment_healthy_crop(self):
        _, farm, crop = self._setup_farmer_farm_crop()
        self._request("POST", f"/api/v1/crops/{crop['id']}/observations", {
            "observation_date": date.today().isoformat(),
            "growth_stage": "maturity",
            "health_status": "healthy",
        })
        code, data = self._request("GET", f"/api/v1/crops/{crop['id']}/decision-assessment")
        self.assertEqual(code, 200)
        health_factor = next(f for f in data["factors"] if f["name"] == "health_status")
        self.assertEqual(health_factor["value"], "healthy")
        self.assertIn("healthy condition", health_factor["observation"])

    def test_harvest_assessment_stressed_and_damaged_crop(self):
        _, farm, crop = self._setup_farmer_farm_crop()
        # Stressed
        self._request("POST", f"/api/v1/crops/{crop['id']}/observations", {
            "observation_date": date.today().isoformat(),
            "growth_stage": "maturity",
            "health_status": "damaged",
        })
        code, data = self._request("GET", f"/api/v1/crops/{crop['id']}/decision-assessment")
        self.assertEqual(code, 200)
        health_factor = next(f for f in data["factors"] if f["name"] == "health_status")
        self.assertEqual(health_factor["value"], "damaged")
        self.assertIn("stress or damage", health_factor["observation"])

    def test_harvest_assessment_stale_observations(self):
        _, farm, crop = self._setup_farmer_farm_crop()
        stale_date = (date.today() - timedelta(days=45)).isoformat()
        self._request("POST", f"/api/v1/crops/{crop['id']}/observations", {
            "observation_date": stale_date,
            "growth_stage": "maturity",
            "health_status": "healthy",
        })
        code, data = self._request("GET", f"/api/v1/crops/{crop['id']}/decision-assessment")
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "insufficient_data")
        self.assertEqual(data["data_sufficiency"], "insufficient")
        recency_factor = next(f for f in data["factors"] if f["name"] == "observation_recency")
        self.assertIn("45 days old", recency_factor["observation"])

    def test_harvest_assessment_weather_data_impact(self):
        _, farm, crop = self._setup_farmer_farm_crop()
        self._request("POST", f"/api/v1/crops/{crop['id']}/observations", {
            "observation_date": date.today().isoformat(),
            "growth_stage": "maturity",
            "health_status": "healthy",
        })

        # Without weather data -> data_sufficiency is 'partial'
        code, data = self._request("GET", f"/api/v1/crops/{crop['id']}/decision-assessment")
        self.assertEqual(code, 200)
        self.assertEqual(data["data_sufficiency"], "partial")
        weather_factor = next(f for f in data["factors"] if f["name"] == "weather_conditions")
        self.assertEqual(weather_factor["value"], "none")

        # Now add weather observation -> data_sufficiency becomes 'sufficient'
        self._request("POST", f"/api/v1/farms/{farm['id']}/weather-observations", {
            "observed_at": "2026-10-02T12:00:00",
            "temperature": 27.5,
            "humidity": 55.0,
            "rainfall": 0.0,
            "wind_speed": 10.0,
        })
        code, data = self._request("GET", f"/api/v1/crops/{crop['id']}/decision-assessment")
        self.assertEqual(code, 200)
        self.assertEqual(data["data_sufficiency"], "sufficient")
        weather_factor = next(f for f in data["factors"] if f["name"] == "weather_conditions")
        self.assertEqual(weather_factor["value"], "1 observations")
        self.assertIn("27.5", weather_factor["observation"])

    # =========================================================================
    # MARKET ASSESSMENT TESTS
    # =========================================================================

    def test_market_assessment_no_observations(self):
        code, data = self._request("GET", "/api/v1/market-decision-assessment?crop_name=Garlic")
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "insufficient_data")
        self.assertEqual(data["data_sufficiency"], "insufficient")
        self.assertEqual(data["crop_name"], "Garlic")
        self.assertTrue(len(data["factors"]) >= 1)
        self.assertEqual(data["factors"][0]["name"], "market_observations")

    def test_market_assessment_one_observation(self):
        self._request("POST", "/api/v1/market-observations", {
            "crop_name": "Onion",
            "market_name": "Lasalgaon APMC",
            "observed_date": "2026-10-01",
            "price": 2000.0,
            "unit": "Rs/Quintal",
        })
        code, data = self._request("GET", "/api/v1/market-decision-assessment?crop_name=Onion")
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "insufficient_data")
        self.assertEqual(data["data_sufficiency"], "insufficient")
        obs_factor = next(f for f in data["factors"] if f["name"] == "observation_count")
        self.assertIn("insufficient historical data", obs_factor["observation"])

    def test_market_assessment_rising_prices(self):
        # 1800 -> 2100 (+16.67%, exceeds +2.0% threshold)
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
            "observed_date": "2026-10-01",
            "price": 2100.0,
            "unit": "Rs/Quintal",
        })
        code, data = self._request("GET", "/api/v1/market-decision-assessment?crop_name=Onion")
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "price_rising")
        self.assertEqual(data["data_sufficiency"], "sufficient")
        trend_factor = next(f for f in data["factors"] if f["name"] == "price_trend")
        self.assertEqual(trend_factor["value"], "price_rising")
        self.assertIn("increased by Rs. 300.0", trend_factor["observation"])

    def test_market_assessment_falling_prices(self):
        # 2000 -> 1700 (-15.0%, below -2.0% threshold)
        self._request("POST", "/api/v1/market-observations", {
            "crop_name": "Tomato",
            "market_name": "Nashik APMC",
            "observed_date": "2026-09-20",
            "price": 2000.0,
            "unit": "Rs/Quintal",
        })
        self._request("POST", "/api/v1/market-observations", {
            "crop_name": "Tomato",
            "market_name": "Nashik APMC",
            "observed_date": "2026-10-01",
            "price": 1700.0,
            "unit": "Rs/Quintal",
        })
        code, data = self._request("GET", "/api/v1/market-decision-assessment?crop_name=Tomato")
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "price_falling")
        self.assertEqual(data["data_sufficiency"], "sufficient")
        trend_factor = next(f for f in data["factors"] if f["name"] == "price_trend")
        self.assertEqual(trend_factor["value"], "price_falling")
        self.assertIn("decreased by Rs. 300.0", trend_factor["observation"])

    def test_market_assessment_stable_prices(self):
        # 2000 -> 2020 (+1.0%, within ±2.0% stability threshold)
        self._request("POST", "/api/v1/market-observations", {
            "crop_name": "Wheat",
            "market_name": "Pune APMC",
            "observed_date": "2026-09-20",
            "price": 2000.0,
            "unit": "Rs/Quintal",
        })
        self._request("POST", "/api/v1/market-observations", {
            "crop_name": "Wheat",
            "market_name": "Pune APMC",
            "observed_date": "2026-10-01",
            "price": 2020.0,
            "unit": "Rs/Quintal",
        })
        code, data = self._request("GET", "/api/v1/market-decision-assessment?crop_name=Wheat")
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "price_stable")
        self.assertEqual(data["data_sufficiency"], "sufficient")
        trend_factor = next(f for f in data["factors"] if f["name"] == "price_trend")
        self.assertEqual(trend_factor["value"], "price_stable")
        self.assertIn("stability band", trend_factor["observation"])

    # =========================================================================
    # ARCHITECTURE & IMMUTABILITY TESTS
    # =========================================================================

    def test_decision_endpoints_do_not_modify_database(self):
        _, farm, crop = self._setup_farmer_farm_crop()
        self._request("POST", f"/api/v1/crops/{crop['id']}/observations", {
            "observation_date": date.today().isoformat(),
            "growth_stage": "maturity",
            "health_status": "healthy",
        })
        self._request("POST", "/api/v1/market-observations", {
            "crop_name": "Onion",
            "market_name": "Lasalgaon APMC",
            "observed_date": "2026-10-01",
            "price": 2000.0,
            "unit": "Rs/Quintal",
        })

        tables = ["farmers", "farms", "crops", "crop_observations", "weather_observations", "market_observations"]
        counts_before = {}
        with self.TestingSessionLocal() as session:
            for t in tables:
                counts_before[t] = session.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()

        # Query decision endpoints repeatedly
        self._request("GET", f"/api/v1/crops/{crop['id']}/decision-assessment")
        self._request("GET", "/api/v1/market-decision-assessment?crop_name=Onion")
        self._request("GET", "/api/v1/market-decision-assessment")

        counts_after = {}
        with self.TestingSessionLocal() as session:
            for t in tables:
                counts_after[t] = session.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()

        self.assertEqual(counts_before, counts_after)


if __name__ == "__main__":
    unittest.main()
