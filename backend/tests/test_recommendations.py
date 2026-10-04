"""
Integration and unit test suite for Milestone 14: Harvest & Sell Recommendation Engine.
Tests decoupled harvest and sell recommendations, transparent confidence levels,
data sufficiency, risk factor reporting, and strict absence of guaranteed claims.
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
from app.models.farmer import Farmer
from app.models.farm import Farm
from app.models.crop import Crop
from app.models.crop_observation import CropObservation
from app.models.weather_observation import WeatherObservation
from app.models.market_observation import MarketObservation
from app.schemas.recommendation import (
    HarvestRecommendation,
    SellRecommendation,
    CropRecommendationResponse,
)
from app.services.harvest_recommendation_service import HarvestRecommendationService
from app.services.sell_recommendation_service import SellRecommendationService
from app.services.recommendation_service import RecommendationService


class TestRecommendations(unittest.TestCase):
    """Verifies all harvest and sell recommendation engine rules and safety guarantees."""

    @classmethod
    def setUpClass(cls):
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

        cls.port = 8804
        cls.base_url = f"http://127.0.0.1:{cls.port}"

        cls.server_config = uvicorn.Config(
            app=app,
            host="127.0.0.1",
            port=cls.port,
            log_level="error",
        )
        cls.server = uvicorn.Server(cls.server_config)
        cls.server_thread = threading.Thread(target=cls.server.run, daemon=True)
        cls.server_thread.start()

        # Wait for server readiness
        max_attempts = 30
        for _ in range(max_attempts):
            try:
                with urlopen(f"{cls.base_url}/api/health", timeout=1.0) as resp:
                    if resp.status == 200:
                        break
            except Exception:
                time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True
        cls.server_thread.join(timeout=2.0)
        app.dependency_overrides.clear()

    def setUp(self):
        with self.test_engine.begin() as conn:
            conn.execute(text("DELETE FROM crop_observations;"))
            conn.execute(text("DELETE FROM weather_observations;"))
            conn.execute(text("DELETE FROM market_observations;"))
            conn.execute(text("DELETE FROM crops;"))
            conn.execute(text("DELETE FROM farms;"))
            conn.execute(text("DELETE FROM farmers;"))

    def _http_get(self, path: str):
        req = Request(f"{self.base_url}{path}", method="GET")
        with urlopen(req, timeout=5.0) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def _assert_no_guaranteed_claims(self, text_list):
        forbidden_phrases = [
            "will definitely",
            "guaranteed",
            "certainly",
            "you will earn more",
            "guaranteed profit",
        ]
        for t in text_list:
            lower = t.lower()
            for phrase in forbidden_phrases:
                self.assertNotIn(
                    phrase,
                    lower,
                    f"Forbidden certainty phrase '{phrase}' found in text: {t}",
                )

    # =========================================================================
    # 1. Harvest Recommendations: harvest_now, approaching_harvest, not_ready
    # =========================================================================

    def test_harvest_now_recommendation(self):
        db = self.TestingSessionLocal()
        try:
            farmer = Farmer(name="Kishore Kumar", phone="9811122233")
            db.add(farmer)
            db.commit()

            farm = Farm(farmer_id=farmer.id, name="Greenfield", location="Nashik", area=4.0, area_unit="acres")
            db.add(farm)
            db.commit()

            crop = Crop(farm_id=farm.id, crop_name="Onion", sowing_date=date.today() - timedelta(days=95), area=2.0, area_unit="acres")
            db.add(crop)
            db.commit()

            # Fresh maturity observation (recorded today)
            obs = CropObservation(crop_id=crop.id, observation_date=date.today(), growth_stage="maturity", health_status="healthy")
            db.add(obs)

            # Weather record
            w = WeatherObservation(farm_id=farm.id, observed_at=datetime.utcnow(), temperature=28.0, humidity=60.0, rainfall=0.0, wind_speed=12.0)
            db.add(w)
            db.commit()
            crop_id = crop.id
        finally:
            db.close()

        status_code, data = self._http_get(f"/api/v1/crops/{crop_id}/recommendation")
        self.assertEqual(status_code, 200)

        h_rec = data["harvest_recommendation"]
        self.assertEqual(h_rec["recommendation"], "harvest_now")
        self.assertEqual(h_rec["status"], "harvest_now")
        self.assertEqual(h_rec["confidence"], "high")
        self.assertEqual(h_rec["data_sufficiency"], "sufficient")
        self.assertTrue(len(h_rec["reasons"]) > 0)
        self.assertIn("maturity", h_rec["reasons"][0].lower())
        self._assert_no_guaranteed_claims(h_rec["reasons"])
        self._assert_no_guaranteed_claims(h_rec["risks"])

    def test_approaching_harvest_recommendation(self):
        db = self.TestingSessionLocal()
        try:
            farmer = Farmer(name="Sanjay Gupta", phone="9822233344")
            db.add(farmer)
            db.commit()

            farm = Farm(farmer_id=farmer.id, name="Valley Farm", location="Pune", area=5.0, area_unit="acres")
            db.add(farm)
            db.commit()

            crop = Crop(farm_id=farm.id, crop_name="Tomato", sowing_date=date.today() - timedelta(days=60), area=1.5, area_unit="acres")
            db.add(crop)
            db.commit()

            obs = CropObservation(crop_id=crop.id, observation_date=date.today(), growth_stage="fruiting", health_status="healthy")
            db.add(obs)
            db.commit()
            crop_id = crop.id
        finally:
            db.close()

        service = HarvestRecommendationService(db)
        try:
            h_rec = service.evaluate_harvest_recommendation(crop_id)
            self.assertEqual(h_rec.recommendation, "approaching_harvest")
            self.assertEqual(h_rec.status, "approaching_harvest")
            self.assertIn("fruiting", h_rec.reasons[0].lower())
            self._assert_no_guaranteed_claims(h_rec.reasons)
        finally:
            db.close()

    def test_not_ready_harvest_recommendation(self):
        db = self.TestingSessionLocal()
        try:
            farmer = Farmer(name="Pooja Mehta", phone="9833344455")
            db.add(farmer)
            db.commit()

            farm = Farm(farmer_id=farmer.id, name="Plateau Farm", location="Nagpur", area=3.0, area_unit="acres")
            db.add(farm)
            db.commit()

            crop = Crop(farm_id=farm.id, crop_name="Cotton", sowing_date=date.today() - timedelta(days=25), area=2.0, area_unit="acres")
            db.add(crop)
            db.commit()

            obs = CropObservation(crop_id=crop.id, observation_date=date.today(), growth_stage="vegetative", health_status="healthy")
            db.add(obs)
            db.commit()
            crop_id = crop.id
        finally:
            db.close()

        service = HarvestRecommendationService(db)
        try:
            h_rec = service.evaluate_harvest_recommendation(crop_id)
            self.assertEqual(h_rec.recommendation, "not_ready")
            self.assertEqual(h_rec.status, "not_ready")
            self.assertIn("vegetative", h_rec.reasons[0].lower())
            self._assert_no_guaranteed_claims(h_rec.reasons)
        finally:
            db.close()

    def test_insufficient_harvest_data_and_stale_observations(self):
        db = self.TestingSessionLocal()
        try:
            farmer = Farmer(name="Vikram Singh", phone="9844455566")
            db.add(farmer)
            db.commit()

            farm = Farm(farmer_id=farmer.id, name="Orchard View", location="Solapur", area=5.0, area_unit="acres")
            db.add(farm)
            db.commit()

            # Crop 1: 0 observations
            crop_no_obs = Crop(farm_id=farm.id, crop_name="Wheat", sowing_date=date.today() - timedelta(days=40), area=2.0, area_unit="acres")
            db.add(crop_no_obs)

            # Crop 2: Stale observation (> 30 days)
            crop_stale = Crop(farm_id=farm.id, crop_name="Barley", sowing_date=date.today() - timedelta(days=80), area=1.0, area_unit="acres")
            db.add(crop_stale)
            db.commit()

            stale_obs = CropObservation(
                crop_id=crop_stale.id,
                observation_date=date.today() - timedelta(days=35),
                growth_stage="flowering",
                health_status="healthy",
            )
            db.add(stale_obs)
            db.commit()

            id_no_obs = crop_no_obs.id
            id_stale = crop_stale.id
        finally:
            db.close()

        service = HarvestRecommendationService(db)
        try:
            # Test 0 observations
            rec1 = service.evaluate_harvest_recommendation(id_no_obs)
            self.assertEqual(rec1.recommendation, "insufficient_data")
            self.assertEqual(rec1.confidence, "insufficient")
            self.assertEqual(rec1.data_sufficiency, "insufficient")
            self.assertTrue(any("no field observations" in r.lower() or "no recorded" in r.lower() for r in rec1.reasons + rec1.risks))

            # Test Stale observation
            rec2 = service.evaluate_harvest_recommendation(id_stale)
            self.assertEqual(rec2.recommendation, "insufficient_data")
            self.assertEqual(rec2.confidence, "insufficient")
            self.assertTrue(any("35 days" in r for r in rec2.reasons + rec2.risks))
        finally:
            db.close()

    # =========================================================================
    # 2. Sell Recommendations: sell_now, hold_for_observation, price_stable, insufficient_data
    # =========================================================================

    def test_sell_now_recommendation_on_falling_market(self):
        db = self.TestingSessionLocal()
        try:
            today = date.today()
            # Downward prices: 2600 -> 2500 -> 2350
            for i, p in enumerate([2600.0, 2500.0, 2350.0]):
                m = MarketObservation(
                    crop_name="Tomato",
                    market_name="Pimpalgaon",
                    observed_date=today - timedelta(days=2 - i),
                    price=p,
                    unit="Rs/Quintal",
                )
                db.add(m)
            db.commit()
        finally:
            db.close()

        service = SellRecommendationService(db)
        try:
            rec = service.evaluate_sell_recommendation(crop_name="Tomato")
            self.assertEqual(rec.recommendation, "sell_now")
            self.assertEqual(rec.status, "sell_now")
            self.assertEqual(rec.confidence, "high")
            self.assertEqual(rec.data_sufficiency, "sufficient")
            self.assertTrue(any("downward" in r.lower() or "decline" in r.lower() for r in rec.reasons))
            self._assert_no_guaranteed_claims(rec.reasons)
            self._assert_no_guaranteed_claims(rec.risks)
        finally:
            db.close()

    def test_hold_for_observation_on_rising_market(self):
        db = self.TestingSessionLocal()
        try:
            today = date.today()
            # Upward prices: 2100 -> 2250 -> 2400
            for i, p in enumerate([2100.0, 2250.0, 2400.0]):
                m = MarketObservation(
                    crop_name="Onion",
                    market_name="Lasalgaon",
                    observed_date=today - timedelta(days=2 - i),
                    price=p,
                    unit="Rs/Quintal",
                )
                db.add(m)
            db.commit()
        finally:
            db.close()

        service = SellRecommendationService(db)
        try:
            rec = service.evaluate_sell_recommendation(crop_name="Onion")
            self.assertEqual(rec.recommendation, "hold_for_observation")
            self.assertEqual(rec.status, "hold_for_observation")
            self.assertEqual(rec.confidence, "high")
            self.assertTrue(any("upward" in r.lower() or "gain" in r.lower() for r in rec.reasons))
            self.assertTrue(any("storage" in r.lower() or "perishable" in r.lower() for r in rec.risks))
            self._assert_no_guaranteed_claims(rec.reasons)
            self._assert_no_guaranteed_claims(rec.risks)
        finally:
            db.close()

    def test_price_stable_recommendation(self):
        db = self.TestingSessionLocal()
        try:
            today = date.today()
            # Stable prices within 2%: 2500 -> 2510 -> 2505
            for i, p in enumerate([2500.0, 2510.0, 2505.0]):
                m = MarketObservation(
                    crop_name="Soybean",
                    market_name="Latur",
                    observed_date=today - timedelta(days=2 - i),
                    price=p,
                    unit="Rs/Quintal",
                )
                db.add(m)
            db.commit()
        finally:
            db.close()

        service = SellRecommendationService(db)
        try:
            rec = service.evaluate_sell_recommendation(crop_name="Soybean")
            self.assertEqual(rec.recommendation, "price_stable")
            self.assertEqual(rec.status, "price_stable")
            self.assertEqual(rec.confidence, "high")
            self.assertTrue(any("stable" in r.lower() or "equilibrium" in r.lower() for r in rec.reasons))
            self._assert_no_guaranteed_claims(rec.reasons)
        finally:
            db.close()

    def test_insufficient_market_data(self):
        db = self.TestingSessionLocal()
        try:
            # 0 observations for Mustard
            service = SellRecommendationService(db)
            rec0 = service.evaluate_sell_recommendation(crop_name="Mustard")
            self.assertEqual(rec0.recommendation, "insufficient_data")
            self.assertEqual(rec0.confidence, "insufficient")
            self.assertEqual(rec0.data_sufficiency, "insufficient")

            # 1 single observation for Groundnut
            m = MarketObservation(
                crop_name="Groundnut",
                market_name="Rajkot",
                observed_date=date.today(),
                price=5500.0,
                unit="Rs/Quintal",
            )
            db.add(m)
            db.commit()

            rec1 = service.evaluate_sell_recommendation(crop_name="Groundnut")
            self.assertEqual(rec1.recommendation, "insufficient_data")
            self.assertEqual(rec1.confidence, "insufficient")
            self.assertEqual(rec1.data_sufficiency, "insufficient")
            self.assertTrue(any("1 market observation" in r.lower() for r in rec1.reasons))
        finally:
            db.close()

    # =========================================================================
    # 3. Decoupled Decisions: Harvest Now + Hold for Observation
    # =========================================================================

    def test_decoupled_harvest_and_sell_decisions(self):
        """Crucial Requirement: Harvest recommendation and Sell recommendation must NOT be coupled."""
        db = self.TestingSessionLocal()
        try:
            farmer = Farmer(name="Deepak Joshi", phone="9855566677")
            db.add(farmer)
            db.commit()

            farm = Farm(farmer_id=farmer.id, name="Sunset Ridge", location="Nashik", area=5.0, area_unit="acres")
            db.add(farm)
            db.commit()

            crop = Crop(farm_id=farm.id, crop_name="Onion (Red)", sowing_date=date.today() - timedelta(days=100), area=2.0, area_unit="acres")
            db.add(crop)
            db.commit()

            # Crop is at MATURITY -> Harvest Now!
            obs = CropObservation(crop_id=crop.id, observation_date=date.today(), growth_stage="maturity", health_status="healthy")
            db.add(obs)

            # Weather is recorded
            w = WeatherObservation(farm_id=farm.id, observed_at=datetime.utcnow(), temperature=29.0, humidity=55.0, rainfall=0.0, wind_speed=11.0)
            db.add(w)

            # Market prices are RISING -> Hold for Observation!
            today = date.today()
            for i, p in enumerate([2200.0, 2350.0, 2500.0]):
                m = MarketObservation(
                    crop_name="Onion (Red)",
                    market_name="Nashik Mandi",
                    observed_date=today - timedelta(days=2 - i),
                    price=p,
                    unit="Rs/Quintal",
                )
                db.add(m)
            db.commit()
            crop_id = crop.id
        finally:
            db.close()

        status_code, data = self._http_get(f"/api/v1/crops/{crop_id}/recommendation")
        self.assertEqual(status_code, 200)

        # Harvest recommendation is harvest_now
        self.assertEqual(data["harvest_recommendation"]["recommendation"], "harvest_now")

        # Sell recommendation is hold_for_observation
        self.assertEqual(data["sell_recommendation"]["recommendation"], "hold_for_observation")

        # Data quality checks
        dq = data["data_quality"]
        self.assertEqual(dq["harvest_data_sufficiency"], "sufficient")
        self.assertEqual(dq["market_data_sufficiency"], "sufficient")
        self.assertEqual(dq["crop_observation_count"], 1)
        self.assertEqual(dq["observation_freshness_days"], 0)
        self.assertEqual(dq["market_observation_count"], 3)
        self.assertTrue(dq["prediction_available"])

    # =========================================================================
    # 4. Error Handling: 404 for non-existent crop
    # =========================================================================

    def test_recommendation_non_existent_crop_returns_404(self):
        with self.assertRaises(HTTPError) as ctx:
            self._http_get("/api/v1/crops/99999/recommendation")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
