"""
Unit and integration test suite for Provider-Independent Data Ingestion Architecture.
Verifies provider contracts, data normalization, physical validation, module isolation,
and integration boundary bridging to existing observation services.
"""

from datetime import date, datetime
import inspect
import sys
import unittest
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlite3 import Connection as SQLite3Connection

from app.db.init_db import init_db
from app.models.base import Base
from app.models.farmer import Farmer
from app.models.farm import Farm
from app.services.farmer_service import FarmerService
from app.services.farm_service import FarmService
from app.services.weather_observation_service import WeatherObservationService
from app.services.market_observation_service import MarketObservationService
from app.schemas.farmer import FarmerCreate
from app.schemas.farm import FarmCreate

# Ingestion imports under test
from app.ingestion.common.types import NormalizedWeatherData, NormalizedMarketData
from app.ingestion.weather.base import WeatherProvider
from app.ingestion.weather.adapters.sample_weather_adapter import SampleWeatherAdapter
from app.ingestion.market.base import MarketProvider
from app.ingestion.market.adapters.sample_market_adapter import SampleMarketAdapter
from app.ingestion.bridge import ingest_weather_observation, ingest_market_observation


class TestDataIngestionArchitecture(unittest.TestCase):
    """Tests contract compliance, data normalization, validation, and layer isolation."""

    @classmethod
    def setUpClass(cls):
        # Configure dedicated isolated in-memory test database for integration boundary tests
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
        Base.metadata.drop_all(bind=self.engine)
        init_db(target_engine=self.engine)
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()

    # =========================================================================
    # 1. PROVIDER INTERFACE CONTRACT TESTS
    # =========================================================================

    def test_weather_provider_interface_contract(self):
        """Verify WeatherProvider cannot be instantiated directly without abstract methods."""
        with self.assertRaises(TypeError):
            WeatherProvider()

        # Concrete adapter satisfies interface
        adapter = SampleWeatherAdapter()
        self.assertIsInstance(adapter, WeatherProvider)
        self.assertEqual(adapter.provider_name, "sample_weather_source")

        # Test interface methods
        current = adapter.fetch_current_observation("Nashik")
        self.assertIsInstance(current, NormalizedWeatherData)

        historical = adapter.fetch_historical_observations("Nashik", date(2026, 10, 1), date(2026, 10, 2))
        self.assertIsInstance(historical, list)
        self.assertIsInstance(historical[0], NormalizedWeatherData)

    def test_market_provider_interface_contract(self):
        """Verify MarketProvider cannot be instantiated directly without abstract methods."""
        with self.assertRaises(TypeError):
            MarketProvider()

        # Concrete adapter satisfies interface
        adapter = SampleMarketAdapter()
        self.assertIsInstance(adapter, MarketProvider)
        self.assertEqual(adapter.provider_name, "sample_mandi_source")

        # Test interface method
        quotes = adapter.fetch_market_observations("Onion", "Lasalgaon APMC")
        self.assertIsInstance(quotes, list)
        self.assertIsInstance(quotes[0], NormalizedMarketData)

    # =========================================================================
    # 2. WEATHER NORMALIZATION & VALIDATION TESTS
    # =========================================================================

    def test_valid_weather_normalization(self):
        """Verify creating NormalizedWeatherData with valid attributes."""
        now = datetime(2026, 10, 2, 14, 30)
        data = NormalizedWeatherData(
            observed_at=now,
            temperature_c=28.5,
            humidity_percent=65.0,
            rainfall_mm=12.2,
            wind_speed_kmh=18.0,
        )
        self.assertEqual(data.observed_at, now)
        self.assertEqual(data.temperature_c, 28.5)
        self.assertEqual(data.humidity_percent, 65.0)
        self.assertEqual(data.rainfall_mm, 12.2)
        self.assertEqual(data.wind_speed_kmh, 18.0)

    def test_weather_adapter_raw_payload_transformation(self):
        """Verify SampleWeatherAdapter parses third-party key mappings accurately."""
        adapter = SampleWeatherAdapter()
        raw = {
            "timestamp": "2026-10-02T12:00:00+00:00",
            "temp_celsius": 31.4,
            "relative_humidity": 45.0,
            "precipitation_mm": 5.2,
            "wind_speed_km_per_hr": 16.5,
        }
        normalized = adapter.transform_raw_payload(raw)
        self.assertIsInstance(normalized, NormalizedWeatherData)
        self.assertEqual(normalized.temperature_c, 31.4)
        self.assertEqual(normalized.humidity_percent, 45.0)
        self.assertEqual(normalized.rainfall_mm, 5.2)
        self.assertEqual(normalized.wind_speed_kmh, 16.5)

    def test_invalid_weather_data_rejection(self):
        """Verify rejection of physically impossible weather parameters."""
        now = datetime.now()

        # Temperature out of bounds (< -50 or > 60)
        with self.assertRaises(ValidationError):
            NormalizedWeatherData(observed_at=now, temperature_c=65.0, humidity_percent=50, rainfall_mm=0, wind_speed_kmh=10)
        with self.assertRaises(ValidationError):
            NormalizedWeatherData(observed_at=now, temperature_c=-55.0, humidity_percent=50, rainfall_mm=0, wind_speed_kmh=10)

        # Humidity out of 0-100 range
        with self.assertRaises(ValidationError):
            NormalizedWeatherData(observed_at=now, temperature_c=25.0, humidity_percent=105.0, rainfall_mm=0, wind_speed_kmh=10)
        with self.assertRaises(ValidationError):
            NormalizedWeatherData(observed_at=now, temperature_c=25.0, humidity_percent=-2.0, rainfall_mm=0, wind_speed_kmh=10)

        # Negative precipitation
        with self.assertRaises(ValidationError):
            NormalizedWeatherData(observed_at=now, temperature_c=25.0, humidity_percent=50.0, rainfall_mm=-1.0, wind_speed_kmh=10)

        # Negative wind speed
        with self.assertRaises(ValidationError):
            NormalizedWeatherData(observed_at=now, temperature_c=25.0, humidity_percent=50.0, rainfall_mm=0.0, wind_speed_kmh=-5.0)

    # =========================================================================
    # 3. MARKET NORMALIZATION & VALIDATION TESTS
    # =========================================================================

    def test_valid_market_normalization(self):
        """Verify creating NormalizedMarketData with valid attributes."""
        today = date(2026, 10, 2)
        data = NormalizedMarketData(
            crop_name="Onion",
            market_name="Lasalgaon APMC",
            observed_date=today,
            price=1950.0,
            unit="Rs/Quintal",
        )
        self.assertEqual(data.crop_name, "Onion")
        self.assertEqual(data.market_name, "Lasalgaon APMC")
        self.assertEqual(data.observed_date, today)
        self.assertEqual(data.price, 1950.0)
        self.assertEqual(data.unit, "Rs/Quintal")

    def test_market_adapter_raw_record_transformation(self):
        """Verify SampleMarketAdapter parses third-party mandi keys accurately."""
        adapter = SampleMarketAdapter()
        raw = {
            "Commodity": "Onion",
            "Market": "Pimpalgaon APMC",
            "Arrival_Date": "2026-10-02",
            "Modal_Price": 1820.0,
            "Price_Unit": "Rs/Quintal",
        }
        normalized = adapter.transform_raw_record(raw)
        self.assertIsInstance(normalized, NormalizedMarketData)
        self.assertEqual(normalized.crop_name, "Onion")
        self.assertEqual(normalized.market_name, "Pimpalgaon APMC")
        self.assertEqual(normalized.price, 1820.0)
        self.assertEqual(normalized.unit, "Rs/Quintal")

    def test_invalid_market_data_rejection(self):
        """Verify rejection of invalid market prices and empty names."""
        today = date.today()

        # Non-positive price
        with self.assertRaises(ValidationError):
            NormalizedMarketData(crop_name="Onion", market_name="Lasalgaon", observed_date=today, price=0.0, unit="Rs/Quintal")
        with self.assertRaises(ValidationError):
            NormalizedMarketData(crop_name="Onion", market_name="Lasalgaon", observed_date=today, price=-100.0, unit="Rs/Quintal")

        # Missing or whitespace-only crop / market / unit
        with self.assertRaises(ValidationError):
            NormalizedMarketData(crop_name="", market_name="Lasalgaon", observed_date=today, price=1500, unit="Rs/Quintal")
        with self.assertRaises(ValidationError):
            NormalizedMarketData(crop_name="   ", market_name="Lasalgaon", observed_date=today, price=1500, unit="Rs/Quintal")
        with self.assertRaises(ValidationError):
            NormalizedMarketData(crop_name="Onion", market_name="  ", observed_date=today, price=1500, unit="Rs/Quintal")
        with self.assertRaises(ValidationError):
            NormalizedMarketData(crop_name="Onion", market_name="Lasalgaon", observed_date=today, price=1500, unit="")

    # =========================================================================
    # 4. MODULE INDEPENDENCE & ARCHITECTURAL BOUNDARY TESTS
    # =========================================================================

    def test_provider_modules_do_not_depend_on_sqlalchemy_or_fastapi(self):
        """
        Architectural assertion: ensures provider and normalized types modules
        contain ZERO imports of sqlalchemy or fastapi.
        """
        ingestion_modules = [
            "app.ingestion.common.types",
            "app.ingestion.weather.base",
            "app.ingestion.weather.adapters.sample_weather_adapter",
            "app.ingestion.market.base",
            "app.ingestion.market.adapters.sample_market_adapter",
        ]

        for mod_name in ingestion_modules:
            mod = sys.modules.get(mod_name)
            self.assertIsNotNone(mod, f"Module {mod_name} should be loaded")
            source = inspect.getsource(mod)

            self.assertNotIn("from sqlalchemy", source, f"{mod_name} must not import sqlalchemy")
            self.assertNotIn("import sqlalchemy", source, f"{mod_name} must not import sqlalchemy")
            self.assertNotIn("from fastapi", source, f"{mod_name} must not import fastapi")
            self.assertNotIn("import fastapi", source, f"{mod_name} must not import fastapi")

    def test_normalized_structures_remain_provider_independent(self):
        """Verifies normalized models forbid extra unknown provider-specific fields and are immutable."""
        now = datetime.now()
        data = NormalizedWeatherData(
            observed_at=now,
            temperature_c=25.0,
            humidity_percent=50.0,
            rainfall_mm=0.0,
            wind_speed_kmh=10.0,
        )

        # Frozen immutability
        with self.assertRaises(ValidationError):
            data.temperature_c = 30.0

        # Extra forbidden fields (cannot smuggle unnormalized provider junk)
        with self.assertRaises(ValidationError):
            NormalizedWeatherData(
                observed_at=now,
                temperature_c=25.0,
                humidity_percent=50.0,
                rainfall_mm=0.0,
                wind_speed_kmh=10.0,
                random_provider_field="junk",
            )

    # =========================================================================
    # 5. INTEGRATION BOUNDARY BRIDGING TO DOMAIN SERVICES
    # =========================================================================

    def test_integration_boundary_weather_ingestion(self):
        """
        Verify the complete ingestion chain:
        Provider Adapter -> Normalized Data -> Validation -> Observation Service -> Repository -> SQLite
        """
        # 1. Setup farm
        farmer_svc = FarmerService(self.db)
        farmer = farmer_svc.create_farmer(FarmerCreate(name="Kisan Ramesh"))
        farm_svc = FarmService(self.db)
        farm = farm_svc.create_farm(FarmCreate(
            farmer_id=farmer.id,
            name="Shree Farm",
            location="Nashik",
            area=3.0,
            area_unit="acre"
        ))

        # 2. Simulate raw provider output -> adapter normalization
        weather_adapter = SampleWeatherAdapter()
        normalized_weather = weather_adapter.transform_raw_payload({
            "timestamp": "2026-10-02T10:00:00+00:00",
            "temp_celsius": 29.5,
            "relative_humidity": 60.0,
            "precipitation_mm": 2.5,
            "wind_speed_km_per_hr": 11.0,
        })

        # 3. Ingest through observation service via bridge
        weather_svc = WeatherObservationService(self.db)
        persisted = ingest_weather_observation(
            farm_id=farm.id,
            data=normalized_weather,
            service=weather_svc,
        )

        self.assertIsNotNone(persisted.id)
        self.assertEqual(persisted.farm_id, farm.id)
        self.assertEqual(persisted.temperature, 29.5)
        self.assertEqual(persisted.rainfall, 2.5)

        # 4. Verify queryable from DB
        stored = weather_svc.get_observations_by_farm(farm.id)
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0].id, persisted.id)

    def test_integration_boundary_market_ingestion(self):
        """
        Verify the complete market ingestion chain:
        Provider Adapter -> Normalized Data -> Validation -> Observation Service -> Repository -> SQLite
        """
        market_adapter = SampleMarketAdapter()
        normalized_market = market_adapter.transform_raw_record({
            "Commodity": "Onion",
            "Market": "Lasalgaon APMC",
            "Arrival_Date": "2026-10-02",
            "Modal_Price": 1880.0,
            "Price_Unit": "Rs/Quintal",
        })

        market_svc = MarketObservationService(self.db)
        persisted = ingest_market_observation(
            data=normalized_market,
            service=market_svc,
        )

        self.assertIsNotNone(persisted.id)
        self.assertEqual(persisted.crop_name, "Onion")
        self.assertEqual(persisted.market_name, "Lasalgaon APMC")
        self.assertEqual(persisted.price, 1880.0)

        # Verify queryable from DB
        stored = market_svc.get_observations(crop_name="Onion")
        self.assertTrue(any(item.id == persisted.id for item in stored))


if __name__ == "__main__":
    unittest.main()
