"""
Unit and integration test suite for Milestone 11: Real Weather and Market Data Integration.
Tests Open-Meteo weather adapter, Government of India OGD mandi adapter,
orchestration services, duplicate protection, coordinate enforcement, and architectural isolation.
All external HTTP requests are mocked in automated tests.
"""

from datetime import date, datetime
import inspect
import io
import json
import unittest
from unittest.mock import MagicMock, patch
import urllib.error

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlite3 import Connection as SQLite3Connection

from app.core.exceptions import BusinessRuleViolationException, EntityNotFoundException
from app.db.init_db import init_db
from app.db.session import get_db
from app.ingestion.market.adapters.ogd_mandi_adapter import OgdMandiAdapter
from app.ingestion.weather.adapters.open_meteo_adapter import OpenMeteoAdapter
from app.main import app
from app.models.farm import Farm
from app.models.farmer import Farmer
from app.schemas.farm import FarmCreate
from app.schemas.farmer import FarmerCreate
from app.services.farm_service import FarmService
from app.services.farmer_service import FarmerService
from app.services.market_ingestion_service import MarketIngestionService
from app.services.weather_ingestion_service import WeatherIngestionService


class TestMilestone11RealIngestion(unittest.TestCase):
    """Automated test suite for Milestone 11 providers, services, and endpoints."""

    @classmethod
    def setUpClass(cls):
        # Configure dedicated in-memory test database
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )

        @event.listens_for(cls.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            if isinstance(dbapi_connection, SQLite3Connection):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        init_db(target_engine=cls.engine)
        cls.SessionLocal = sessionmaker(bind=cls.engine, expire_on_commit=False)

    def setUp(self):
        self.db = self.SessionLocal()
        farmer_svc = FarmerService(self.db)
        self.farmer = farmer_svc.create_farmer(FarmerCreate(name="Balasaheb Patil", phone="9822011111"))

        farm_svc = FarmService(self.db)
        # Farm with valid coordinates in location
        self.farm_with_coords = farm_svc.create_farm(
            FarmCreate(
                farmer_id=self.farmer.id,
                name="Godavari Orchards",
                location="20.0063, 73.7902",
                area=5.0,
                area_unit="acre",
            )
        )
        # Farm with named location without coordinates
        self.farm_named_location = farm_svc.create_farm(
            FarmCreate(
                farmer_id=self.farmer.id,
                name="Shiva Mala Shivar",
                location="Niphad, Nashik",
                area=3.5,
                area_unit="acre",
            )
        )

    def tearDown(self):
        self.db.query(Farm).delete()
        self.db.query(Farmer).delete()
        self.db.commit()
        self.db.close()

    # =========================================================================
    # 1. Open-Meteo Weather Adapter Tests
    # =========================================================================

    def test_open_meteo_coordinate_parsing_valid(self):
        adapter = OpenMeteoAdapter()
        lat, lon = adapter.parse_coordinates("19.9975, 73.7898")
        self.assertAlmostEqual(lat, 19.9975)
        self.assertAlmostEqual(lon, 73.7898)

    def test_open_meteo_coordinate_parsing_invalid(self):
        adapter = OpenMeteoAdapter()
        with self.assertRaises(ValueError):
            adapter.parse_coordinates("Nashik, Maharashtra")  # Named locality rejected

        with self.assertRaises(ValueError):
            adapter.parse_coordinates("95.0, 73.0")  # Latitude out of bounds

        with self.assertRaises(ValueError):
            adapter.parse_coordinates("20.0, 200.0")  # Longitude out of bounds

    @patch("urllib.request.urlopen")
    def test_open_meteo_fetch_current_observation_success(self, mock_urlopen):
        mock_response = io.BytesIO(
            json.dumps({
                "latitude": 20.0,
                "longitude": 73.8,
                "current": {
                    "time": "2026-10-02T12:00",
                    "temperature_2m": 29.4,
                    "relative_humidity_2m": 58.0,
                    "precipitation": 0.0,
                    "wind_speed_10m": 11.2,
                },
            }).encode("utf-8")
        )
        mock_urlopen.return_value.__enter__.return_value = mock_response

        adapter = OpenMeteoAdapter()
        obs = adapter.fetch_current_observation("20.0, 73.8")
        self.assertEqual(obs.temperature_c, 29.4)
        self.assertEqual(obs.humidity_percent, 58.0)
        self.assertEqual(obs.rainfall_mm, 0.0)
        self.assertEqual(obs.wind_speed_kmh, 11.2)
        self.assertEqual(obs.observed_at, datetime(2026, 10, 2, 12, 0))

    @patch("urllib.request.urlopen")
    def test_open_meteo_fetch_recent_observations_hourly_normalization(self, mock_urlopen):
        # 3 hourly samples
        payload = {
            "hourly": {
                "time": ["2026-10-02T01:00", "2026-10-02T02:00", "2026-10-02T03:00"],
                "temperature_2m": [22.1, 21.8, 21.5],
                "relative_humidity_2m": [75.0, 78.0, 80.0],
                "precipitation": [0.0, 0.5, 1.2],
                "wind_speed_10m": [8.0, 7.5, 6.0],
            }
        }
        mock_urlopen.return_value.__enter__.return_value = io.BytesIO(json.dumps(payload).encode("utf-8"))

        adapter = OpenMeteoAdapter()
        records = adapter.fetch_recent_observations("20.0, 73.8", past_days=1)
        self.assertEqual(len(records), 3)
        self.assertEqual(records[0].temperature_c, 22.1)
        self.assertEqual(records[1].rainfall_mm, 0.5)
        self.assertEqual(records[2].humidity_percent, 80.0)

    @patch("urllib.request.urlopen")
    def test_open_meteo_missing_required_fields_raises_error(self, mock_urlopen):
        # Missing 'temperature_2m' in current
        payload = {
            "current": {
                "time": "2026-10-02T12:00",
                "relative_humidity_2m": 58.0,
                "precipitation": 0.0,
                "wind_speed_10m": 11.2,
            }
        }
        mock_urlopen.return_value.__enter__.return_value = io.BytesIO(json.dumps(payload).encode("utf-8"))

        adapter = OpenMeteoAdapter()
        with self.assertRaises(ValueError):
            adapter.fetch_current_observation("20.0, 73.8")

    @patch("urllib.request.urlopen")
    def test_open_meteo_http_error_handling(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://api.open-meteo.com/v1/forecast",
            code=500,
            msg="Internal Server Error",
            hdrs={},
            fp=io.BytesIO(b"Server error"),
        )
        adapter = OpenMeteoAdapter()
        with self.assertRaises(RuntimeError) as ctx:
            adapter.fetch_current_observation("20.0, 73.8")
        self.assertIn("HTTP error 500", str(ctx.exception))

    # =========================================================================
    # 2. Government of India OGD Mandi Adapter Tests
    # =========================================================================

    def test_ogd_missing_api_key_raises_runtime_error(self):
        adapter = OgdMandiAdapter(api_key=None)
        with self.assertRaises(RuntimeError) as ctx:
            adapter.fetch_market_observations("Onion")
        self.assertIn("OGD_API_KEY", str(ctx.exception))

    @patch("urllib.request.urlopen")
    def test_ogd_fetch_market_observations_success(self, mock_urlopen):
        payload = {
            "status": "ok",
            "records": [
                {
                    "commodity": "Onion",
                    "market": "Lasalgaon APMC",
                    "arrival_date": "02/10/2026",
                    "modal_price": "2350.00",
                    "unit": "Rs/Quintal",
                },
                {
                    "commodity": "Onion",
                    "market": "Pimpalgaon APMC",
                    "arrival_date": "02/10/2026",
                    "modal_price": "2420.00",
                    "unit": "Rs/Quintal",
                },
            ],
        }
        mock_urlopen.return_value.__enter__.return_value = io.BytesIO(json.dumps(payload).encode("utf-8"))

        adapter = OgdMandiAdapter(api_key="test-mock-key")
        records = adapter.fetch_market_observations("Onion")
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].crop_name, "Onion")
        self.assertEqual(records[0].market_name, "Lasalgaon APMC")
        self.assertEqual(records[0].price, 2350.0)
        self.assertEqual(records[0].observed_date, date(2026, 10, 2))
        self.assertEqual(records[0].unit, "Rs/Quintal")

    @patch("urllib.request.urlopen")
    def test_ogd_invalid_price_skipped_cleanly(self, mock_urlopen):
        payload = {
            "status": "ok",
            "records": [
                {
                    "commodity": "Onion",
                    "market": "Lasalgaon",
                    "arrival_date": "02/10/2026",
                    "modal_price": "-100",  # Negative price
                },
                {
                    "commodity": "Onion",
                    "market": "Lasalgaon",
                    "arrival_date": "02/10/2026",
                    "modal_price": "invalid",  # Non-numeric price
                },
                {
                    "commodity": "Onion",
                    "market": "Lasalgaon",
                    "arrival_date": "02/10/2026",
                    "modal_price": "2200",  # Valid
                },
            ],
        }
        mock_urlopen.return_value.__enter__.return_value = io.BytesIO(json.dumps(payload).encode("utf-8"))

        adapter = OgdMandiAdapter(api_key="test-mock-key")
        records = adapter.fetch_market_observations("Onion")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].price, 2200.0)

    # =========================================================================
    # 3. Weather Ingestion Service & Duplicate Protection Tests
    # =========================================================================

    @patch("urllib.request.urlopen")
    def test_weather_ingestion_service_with_farm_coordinates(self, mock_urlopen):
        payload = {
            "hourly": {
                "time": ["2026-10-02T10:00", "2026-10-02T11:00"],
                "temperature_2m": [28.0, 29.0],
                "relative_humidity_2m": [60.0, 55.0],
                "precipitation": [0.0, 0.0],
                "wind_speed_10m": [10.0, 12.0],
            }
        }
        mock_urlopen.return_value.__enter__.return_value = io.BytesIO(json.dumps(payload).encode("utf-8"))

        service = WeatherIngestionService(self.db)
        res = service.sync_farm_weather(self.farm_with_coords.id)
        self.assertEqual(res["records_received"], 2)
        self.assertEqual(res["records_accepted"], 2)
        self.assertEqual(res["records_rejected"], 0)

        # Immediate repeat sync with same data: duplicate protection test
        mock_urlopen.return_value.__enter__.return_value = io.BytesIO(json.dumps(payload).encode("utf-8"))
        res2 = service.sync_farm_weather(self.farm_with_coords.id)
        self.assertEqual(res2["records_received"], 2)
        self.assertEqual(res2["records_accepted"], 0)  # Both rejected as duplicates
        self.assertEqual(res2["records_rejected"], 2)

    def test_weather_ingestion_rejects_named_location_without_coordinates(self):
        service = WeatherIngestionService(self.db)
        with self.assertRaises(BusinessRuleViolationException) as ctx:
            service.sync_farm_weather(self.farm_named_location.id)
        self.assertIn("Coordinates (latitude and longitude) are required", str(ctx.exception))
        self.assertIn("Automatic geocoding is disabled", str(ctx.exception))

    @patch("urllib.request.urlopen")
    def test_weather_ingestion_accepts_manual_coordinate_override(self, mock_urlopen):
        payload = {
            "hourly": {
                "time": ["2026-10-02T08:00"],
                "temperature_2m": [25.0],
                "relative_humidity_2m": [70.0],
                "precipitation": [0.0],
                "wind_speed_10m": [5.0],
            }
        }
        mock_urlopen.return_value.__enter__.return_value = io.BytesIO(json.dumps(payload).encode("utf-8"))

        service = WeatherIngestionService(self.db)
        # Even though farm location is "Niphad, Nashik", manual coordinates override
        res = service.sync_farm_weather(
            self.farm_named_location.id,
            latitude=20.0894,
            longitude=74.1086,
        )
        self.assertEqual(res["records_accepted"], 1)

    # =========================================================================
    # 4. Market Ingestion Service & Duplicate Protection Tests
    # =========================================================================

    @patch("urllib.request.urlopen")
    def test_market_ingestion_service_duplicate_protection(self, mock_urlopen):
        payload = {
            "status": "ok",
            "records": [
                {
                    "commodity": "Onion",
                    "market": "Lasalgaon",
                    "arrival_date": "02/10/2026",
                    "modal_price": "2100",
                },
                # Duplicate within the same batch
                {
                    "commodity": "Onion",
                    "market": "Lasalgaon",
                    "arrival_date": "02/10/2026",
                    "modal_price": "2100",
                },
            ],
        }
        mock_urlopen.return_value.__enter__.return_value = io.BytesIO(json.dumps(payload).encode("utf-8"))

        adapter = OgdMandiAdapter(api_key="test-key")
        service = MarketIngestionService(self.db, market_provider=adapter)
        res = service.sync_market_data(crop_name="Onion")
        self.assertEqual(res["records_received"], 2)
        self.assertEqual(res["records_accepted"], 1)  # 1 accepted, 1 in-batch duplicate rejected
        self.assertEqual(res["records_rejected"], 1)

        # Subsequent sync with same record
        mock_urlopen.return_value.__enter__.return_value = io.BytesIO(json.dumps(payload).encode("utf-8"))
        res2 = service.sync_market_data(crop_name="Onion")
        self.assertEqual(res2["records_received"], 2)
        self.assertEqual(res2["records_accepted"], 0)  # 0 accepted, both DB & batch duplicates
        self.assertEqual(res2["records_rejected"], 2)

    # =========================================================================
    # 5. Architecture Isolation Tests
    # =========================================================================

    def test_adapters_contain_no_sqlalchemy_or_fastapi(self):
        """Verifies that adapters have zero coupling with SQLAlchemy or FastAPI."""
        import app.ingestion.weather.adapters.open_meteo_adapter as weather_mod
        import app.ingestion.market.adapters.ogd_mandi_adapter as market_mod

        weather_src = inspect.getsource(weather_mod)
        market_src = inspect.getsource(market_mod)

        for src, name in [(weather_src, "OpenMeteoAdapter"), (market_src, "OgdMandiAdapter")]:
            self.assertNotIn("sqlalchemy", src.lower(), f"{name} must not import SQLAlchemy")
            self.assertNotIn("fastapi", src.lower(), f"{name} must not import FastAPI")
            self.assertNotIn("starlette", src.lower(), f"{name} must not import Starlette")

    # =========================================================================
    # 6. Manual Sync API Endpoints Tests
    # =========================================================================

    def test_sync_endpoints_direct_calls(self):
        from fastapi import HTTPException
        from app.api.endpoints.sync import sync_farm_weather, sync_market_data
        from app.schemas.sync import MarketSyncRequest, WeatherSyncRequest

        # Missing farm 404 test
        with self.assertRaises(HTTPException) as ctx:
            sync_farm_weather(farm_id=9999, payload=None, db=self.db)
        self.assertEqual(ctx.exception.status_code, 404)

        # Farm without coordinates 400 test
        with self.assertRaises(HTTPException) as ctx:
            sync_farm_weather(farm_id=self.farm_named_location.id, payload=None, db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Coordinates", ctx.exception.detail)

        # Market sync without configured key returns 400 with explanation
        with self.assertRaises(HTTPException) as ctx:
            sync_market_data(payload=MarketSyncRequest(crop_name="Onion"), db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("OGD_API_KEY", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()
