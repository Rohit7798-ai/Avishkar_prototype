"""
Integration and unit test suite for Milestone 13: AI Explanation Layer.
Tests structured explanation generation, provider decoupling,
grounding across Observed, Calculated, Predicted, and Assessment categories,
and strict avoidance of directive harvest/sell advice.
"""

from datetime import date, datetime, timedelta
import json
from sqlite3 import Connection as SQLite3Connection
import threading
import time
from typing import Any, Dict, Optional
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
from app.models.farmer import Farmer
from app.models.farm import Farm
from app.models.crop import Crop
from app.models.crop_observation import CropObservation
from app.models.weather_observation import WeatherObservation
from app.models.market_observation import MarketObservation
from app.schemas.explanation import (
    ObservedDataBreakdown,
    CalculatedDataBreakdown,
    PredictedDataBreakdown,
    AssessmentDataBreakdown,
    CropExplanationResponse,
)
from app.services.explanation_service import (
    ExplanationProvider,
    ExplanationService,
    RuleBasedExplanationProvider,
)


class TestExplanationLayer(unittest.TestCase):
    """Verifies all explanation layer requirements, safety bounds, and API contracts."""

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

        cls.port = 8802
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
        # Clean in-memory tables before each test
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

    def _assert_no_forbidden_directive_advice(self, text_content: str):
        """Guardrail: Explanations must strictly avoid directive recommendation language."""
        forbidden_phrases = [
            "you should sell",
            "you should harvest",
            "wait to sell",
            "harvest immediately",
            "guaranteed",
            "will definitely",
        ]
        lower_text = text_content.lower()
        for phrase in forbidden_phrases:
            self.assertNotIn(
                phrase,
                lower_text,
                f"Forbidden directive phrase '{phrase}' found in explanation text: {text_content}",
            )

    # =========================================================================
    # 1. Complete Data Scenario Test
    # =========================================================================

    def test_complete_data_explanation_success(self):
        db = self.TestingSessionLocal()
        try:
            farmer = Farmer(name="Ramesh Patel", phone="9876543210")
            db.add(farmer)
            db.commit()

            farm = Farm(farmer_id=farmer.id, name="Green Acres", location="Nashik, Maharashtra", area=5.0, area_unit="acres")
            db.add(farm)
            db.commit()

            crop = Crop(
                farm_id=farm.id,
                crop_name="Onion (Red)",
                variety="Garwa",
                sowing_date=date.today() - timedelta(days=90),
                area=2.0,
                area_unit="acres",
            )
            db.add(crop)
            db.commit()

            # Crop observation: maturity reached
            crop_obs = CropObservation(
                crop_id=crop.id,
                observation_date=date.today(),
                growth_stage="maturity",
                health_status="healthy",
                notes="Bulbs fully developed with dry outer scales.",
            )
            db.add(crop_obs)

            # Weather observations
            base_time = datetime.utcnow()
            for i, (temp, hum, rain, wind) in enumerate([
                (28.5, 60.0, 0.0, 12.0),
                (29.0, 58.0, 0.0, 14.0),
                (30.0, 55.0, 0.0, 10.0),
            ]):
                w = WeatherObservation(
                    farm_id=farm.id,
                    observed_at=base_time - timedelta(days=2 - i),
                    temperature=temp,
                    humidity=hum,
                    rainfall=rain,
                    wind_speed=wind,
                )
                db.add(w)

            # Market observations for Onion (Red)
            today = date.today()
            for i, p in enumerate([2400.0, 2450.0, 2550.0]):
                m = MarketObservation(
                    crop_name="Onion (Red)",
                    market_name="Lasalgaon",
                    observed_date=today - timedelta(days=2 - i),
                    price=p,
                    unit="Rs/Quintal",
                )
                db.add(m)

            db.commit()
            crop_id = crop.id
        finally:
            db.close()

        status_code, data = self._http_get(f"/api/v1/crops/{crop_id}/explanation")
        self.assertEqual(status_code, 200)

        # Verify Top-level fields
        self.assertEqual(data["crop_id"], crop_id)
        self.assertEqual(data["crop_name"], "Onion (Red)")
        self.assertEqual(data["farm_name"], "Green Acres")
        self.assertEqual(data["farm_location"], "Nashik, Maharashtra")
        self.assertEqual(data["provider"], "rule-based-deterministic")

        # Verify Breakdown Categories
        obs = data["observations"]
        self.assertEqual(obs["crop_stage"], "maturity")
        self.assertEqual(obs["crop_health"], "healthy")
        self.assertEqual(obs["crop_observations_count"], 1)
        self.assertEqual(obs["weather_observations_count"], 3)
        self.assertEqual(obs["market_observations_count"], 3)
        self.assertEqual(obs["latest_market_price"], 2550.0)

        calc = data["calculated"]
        self.assertEqual(calc["days_since_latest_crop_observation"], 0)
        self.assertAlmostEqual(calc["market_price_change"], 150.0)
        self.assertTrue(calc["market_price_change_percentage"] > 0)
        self.assertIsNotNone(calc["average_temperature_c"])

        pred = data["predicted"]
        self.assertIsNotNone(pred)
        self.assertIsNotNone(pred["predicted_next_modal_price"])
        self.assertIn(pred["direction"], ["higher", "lower", "unchanged"])
        self.assertEqual(pred["currency"], "Rs/Quintal")

        assessment = data["assessment"]
        self.assertEqual(assessment["harvest_status"], "maturity_observed")
        self.assertEqual(assessment["market_trend_status"], "price_rising")

        # Verify Explanations exist and are farmer-friendly
        self.assertTrue(len(data["summary"]) > 20)
        self.assertIn("maturity", data["decision_explanation"])
        self.assertIn("Green Acres", data["summary"])
        self.assertIn("recorded weather", data["weather_explanation"])
        self.assertIn("Mandi price records", data["market_explanation"])
        self.assertIn("baseline statistical model", data["prediction_explanation"])

        # Limitations present
        self.assertTrue(len(data["limitations"]) >= 4)

        # Guardrail checks across all explanation text fields
        self._assert_no_forbidden_directive_advice(data["summary"])
        self._assert_no_forbidden_directive_advice(data["decision_explanation"])
        self._assert_no_forbidden_directive_advice(data["weather_explanation"])
        self._assert_no_forbidden_directive_advice(data["market_explanation"])
        self._assert_no_forbidden_directive_advice(data["prediction_explanation"])

    # =========================================================================
    # 2. Missing Crop Observations Test
    # =========================================================================

    def test_missing_crop_observations_explanation(self):
        db = self.TestingSessionLocal()
        try:
            farmer = Farmer(name="Suresh Rao", phone="9123456780")
            db.add(farmer)
            db.commit()

            farm = Farm(farmer_id=farmer.id, name="Sunrise Fields", location="Pune", area=4.0, area_unit="acres")
            db.add(farm)
            db.commit()

            crop = Crop(farm_id=farm.id, crop_name="Wheat", sowing_date=date.today() - timedelta(days=20), area=1.5, area_unit="acres")
            db.add(crop)
            db.commit()
            crop_id = crop.id
        finally:
            db.close()

        status_code, data = self._http_get(f"/api/v1/crops/{crop_id}/explanation")
        self.assertEqual(status_code, 200)

        self.assertEqual(data["observations"]["crop_observations_count"], 0)
        self.assertIsNone(data["observations"]["crop_stage"])
        self.assertEqual(data["assessment"]["harvest_status"], "insufficient_data")
        self.assertIn("No crop observations have been recorded", data["decision_explanation"])
        self.assertIn("Field scouting is necessary", data["decision_explanation"])
        self.assertIsNone(data["predicted"])
        self.assertIn("not available", data["prediction_explanation"])

    # =========================================================================
    # 3. Stale Observations Test (> 30 Days)
    # =========================================================================

    def test_stale_observations_explanation(self):
        db = self.TestingSessionLocal()
        try:
            farmer = Farmer(name="Vijay Kumar", phone="9876500000")
            db.add(farmer)
            db.commit()

            farm = Farm(farmer_id=farmer.id, name="Riverbend Farm", location="Satara", area=6.0, area_unit="acres")
            db.add(farm)
            db.commit()

            crop = Crop(farm_id=farm.id, crop_name="Tomato", sowing_date=date.today() - timedelta(days=100), area=2.0, area_unit="acres")
            db.add(crop)
            db.commit()

            # Stale observation: 40 days ago
            stale_obs = CropObservation(
                crop_id=crop.id,
                observation_date=date.today() - timedelta(days=40),
                growth_stage="flowering",
                health_status="healthy",
                notes="Early flowering stage recorded.",
            )
            db.add(stale_obs)
            db.commit()
            crop_id = crop.id
        finally:
            db.close()

        status_code, data = self._http_get(f"/api/v1/crops/{crop_id}/explanation")
        self.assertEqual(status_code, 200)

        self.assertEqual(data["assessment"]["harvest_status"], "insufficient_data")
        self.assertEqual(data["calculated"]["days_since_latest_crop_observation"], 40)
        self.assertIn("40 days ago", data["decision_explanation"])
        self.assertIn("fresh field scouting is required", data["decision_explanation"])

    # =========================================================================
    # 4. Single Market Observation Test
    # =========================================================================

    def test_single_market_observation_explanation(self):
        db = self.TestingSessionLocal()
        try:
            farmer = Farmer(name="Anita Sharma", phone="9876511111")
            db.add(farmer)
            db.commit()

            farm = Farm(farmer_id=farmer.id, name="Hillside Farm", location="Nagpur", area=3.0, area_unit="acres")
            db.add(farm)
            db.commit()

            crop = Crop(farm_id=farm.id, crop_name="Soybean", sowing_date=date.today() - timedelta(days=40), area=1.0, area_unit="acres")
            db.add(crop)
            db.commit()

            crop_obs = CropObservation(
                crop_id=crop.id,
                observation_date=date.today(),
                growth_stage="vegetative",
                health_status="healthy",
            )
            db.add(crop_obs)

            # Single market observation
            market_obs = MarketObservation(
                crop_name="Soybean",
                market_name="Nagpur Mandi",
                observed_date=date.today(),
                price=4200.0,
                unit="Rs/Quintal",
            )
            db.add(market_obs)
            db.commit()
            crop_id = crop.id
        finally:
            db.close()

        status_code, data = self._http_get(f"/api/v1/crops/{crop_id}/explanation")
        self.assertEqual(status_code, 200)

        self.assertEqual(data["observations"]["market_observations_count"], 1)
        self.assertIn("single mandi observation", data["market_explanation"].lower())
        self.assertIn("additional daily observations are needed", data["market_explanation"].lower())

    # =========================================================================
    # 5. Provider Independence Unit Test
    # =========================================================================

    def test_provider_independence_mock(self):
        db = self.TestingSessionLocal()
        try:
            farmer = Farmer(name="Test Farmer", phone="9999988888")
            db.add(farmer)
            db.commit()

            farm = Farm(farmer_id=farmer.id, name="Test Farm", location="Test Loc", area=2.0, area_unit="acres")
            db.add(farm)
            db.commit()

            crop = Crop(farm_id=farm.id, crop_name="Cotton", sowing_date=date.today() - timedelta(days=30), area=1.0, area_unit="acres")
            db.add(crop)
            db.commit()

            class CustomMockProvider(ExplanationProvider):
                def generate_explanation(self, crop_name, farm_name, farm_location, observed, calculated, predicted, assessment):
                    return {
                        "summary": f"Custom mock summary for {crop_name}.",
                        "decision_explanation": "Custom decision explanation.",
                        "weather_explanation": "Custom weather explanation.",
                        "market_explanation": "Custom market explanation.",
                        "prediction_explanation": "Custom prediction explanation.",
                        "limitations": ["Custom mock limitation."],
                        "provider_name": "custom-mock-ai-provider",
                    }

            service = ExplanationService(db=db, provider=CustomMockProvider())
            explanation = service.get_crop_explanation(crop.id)

            self.assertEqual(explanation.provider, "custom-mock-ai-provider")
            self.assertEqual(explanation.summary, "Custom mock summary for Cotton.")
            self.assertEqual(explanation.limitations, ["Custom mock limitation."])
        finally:
            db.close()

    # =========================================================================
    # 6. Non-Existent Crop 404 Test
    # =========================================================================

    def test_non_existent_crop_returns_404(self):
        with self.assertRaises(HTTPError) as ctx:
            self._http_get("/api/v1/crops/99999/explanation")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
