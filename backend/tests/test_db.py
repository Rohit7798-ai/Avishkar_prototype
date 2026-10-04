"""
Unit and integration tests for Database Configuration, Domain Models, and Relationships.
Uses Python's standard library `unittest` and an isolated in-memory SQLite database
to ensure zero external dependencies and fast, hermetic execution.
"""

from datetime import date, datetime
from sqlite3 import Connection as SQLite3Connection
import unittest

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.db.init_db import init_db
from app.models.base import Base
from app.models.farmer import Farmer
from app.models.farm import Farm
from app.models.crop import Crop
from app.schemas.farmer import FarmerCreate, FarmerResponse
from app.schemas.farm import AreaUnit, FarmCreate, FarmResponse
from app.schemas.crop import CropCreate, CropResponse
from pydantic import ValidationError


class TestDatabaseAndDomainModels(unittest.TestCase):
    """Test suite covering Milestone 3 database domain models and constraints."""

    def setUp(self):
        # Create an isolated in-memory SQLite database engine with foreign keys enabled
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            future=True,
        )

        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            if isinstance(dbapi_connection, SQLite3Connection):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        # Build tables using the safe initialization mechanism
        init_db(target_engine=self.engine)

        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    # 1. Database connection test
    def test_database_connection(self):
        """Verify the database engine establishes an active, queryable connection."""
        with self.engine.connect() as conn:
            result = conn.exec_driver_sql("SELECT 1").scalar()
            self.assertEqual(result, 1)

    # 2. Table creation test
    def test_table_creation(self):
        """Verify that farmers, farms, and crops tables are created with proper columns."""
        inspector = inspect(self.engine)
        table_names = inspector.get_table_names()

        self.assertIn("farmers", table_names)
        self.assertIn("farms", table_names)
        self.assertIn("crops", table_names)

        # Verify farmer columns
        farmer_cols = {col["name"] for col in inspector.get_columns("farmers")}
        self.assertTrue({"id", "name", "phone", "created_at", "updated_at"}.issubset(farmer_cols))

        # Verify farm columns
        farm_cols = {col["name"] for col in inspector.get_columns("farms")}
        self.assertTrue({"id", "farmer_id", "name", "location", "area", "area_unit", "created_at", "updated_at"}.issubset(farm_cols))

        # Verify crop columns
        crop_cols = {col["name"] for col in inspector.get_columns("crops")}
        self.assertTrue({"id", "farm_id", "crop_name", "variety", "sowing_date", "expected_harvest_date", "area", "area_unit", "created_at", "updated_at"}.issubset(crop_cols))

    # 3. Farmer -> Farm relationship test
    def test_farmer_farm_relationship(self):
        """Verify that a farmer can own multiple farms and bi-directional relationships resolve."""
        farmer = Farmer(name="Ramesh Patil", phone="+919823012345")
        self.db.add(farmer)
        self.db.commit()
        self.db.refresh(farmer)

        farm1 = Farm(farmer_id=farmer.id, name="North Parcel", location="Niphad, Nashik", area=4.5, area_unit="acre")
        farm2 = Farm(farmer_id=farmer.id, name="South Parcel", location="Dindori, Nashik", area=2.0, area_unit="hectare")
        self.db.add_all([farm1, farm2])
        self.db.commit()

        # Query farmer and inspect farms relationship
        queried_farmer = self.db.query(Farmer).filter_by(id=farmer.id).one()
        self.assertEqual(len(queried_farmer.farms), 2)
        farm_names = {f.name for f in queried_farmer.farms}
        self.assertEqual(farm_names, {"North Parcel", "South Parcel"})

        # Verify reverse relation
        self.assertEqual(farm1.farmer.name, "Ramesh Patil")

    # 4. Farm -> Crop relationship test
    def test_farm_crop_relationship(self):
        """Verify that a farm can contain multiple crops and bi-directional relationships resolve."""
        farmer = Farmer(name="Sunil Shinde", phone="+919823098765")
        self.db.add(farmer)
        self.db.commit()

        farm = Farm(farmer_id=farmer.id, name="Main Field", location="Lasalgaon, Nashik", area=5.0, area_unit="acre")
        self.db.add(farm)
        self.db.commit()

        crop1 = Crop(
            farm_id=farm.id,
            crop_name="Onion",
            variety="Bhima Super",
            sowing_date=date(2026, 6, 15),
            expected_harvest_date=date(2026, 10, 15),
            area=3.0,
            area_unit="acre",
        )
        crop2 = Crop(
            farm_id=farm.id,
            crop_name="Soybean",
            variety="JS-335",
            sowing_date=date(2026, 6, 20),
            area=2.0,
            area_unit="acre",
        )
        self.db.add_all([crop1, crop2])
        self.db.commit()

        queried_farm = self.db.query(Farm).filter_by(id=farm.id).one()
        self.assertEqual(len(queried_farm.crops), 2)
        crop_names = {c.crop_name for c in queried_farm.crops}
        self.assertEqual(crop_names, {"Onion", "Soybean"})

        # Verify reverse relation
        self.assertEqual(crop1.farm.name, "Main Field")

    # 5. Foreign-key constraint and cascading behavior test
    def test_foreign_key_and_cascade_behavior(self):
        """Verify foreign-key violation fails and parent deletion cascades properly."""
        # 5a. Inserting a farm with a non-existent farmer_id must fail
        orphan_farm = Farm(farmer_id=99999, name="Ghost Farm", location="Unknown", area=1.0, area_unit="acre")
        self.db.add(orphan_farm)
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

        # 5b. Inserting a crop with a non-existent farm_id must fail
        orphan_crop = Crop(farm_id=99999, crop_name="Ghost Onion", sowing_date=date.today(), area=1.0, area_unit="acre")
        self.db.add(orphan_crop)
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

        # 5c. Cascading delete verification
        farmer = Farmer(name="Dattatray Kadam")
        self.db.add(farmer)
        self.db.commit()

        farm = Farm(farmer_id=farmer.id, name="Cascade Farm", location="Niphad", area=3.0, area_unit="acre")
        self.db.add(farm)
        self.db.commit()

        crop = Crop(farm_id=farm.id, crop_name="Onion", sowing_date=date.today(), area=3.0, area_unit="acre")
        self.db.add(crop)
        self.db.commit()

        farmer_id = farmer.id
        farm_id = farm.id
        crop_id = crop.id

        # Deleting the farmer must cascade-delete their farms and crops
        self.db.delete(farmer)
        self.db.commit()

        self.assertIsNone(self.db.query(Farmer).filter_by(id=farmer_id).first())
        self.assertIsNone(self.db.query(Farm).filter_by(id=farm_id).first())
        self.assertIsNone(self.db.query(Crop).filter_by(id=crop_id).first())

    # 6. Database initialization idempotency test
    def test_init_db_idempotency(self):
        """Verify calling init_db multiple times does not error or duplicate schema."""
        # Re-run init_db on the existing engine
        init_db(target_engine=self.engine)
        init_db(target_engine=self.engine)

        # Existing tables must still be queryable without error
        inspector = inspect(self.engine)
        self.assertEqual(len(inspector.get_table_names()), len(Base.metadata.tables))

        # Verify no fake data was seeded
        farmer_count = self.db.query(Farmer).count()
        farm_count = self.db.query(Farm).count()
        crop_count = self.db.query(Crop).count()
        self.assertEqual(farmer_count, 0)
        self.assertEqual(farm_count, 0)
        self.assertEqual(crop_count, 0)

    # 7. Pydantic schemas validation and ORM mapping test
    def test_pydantic_schemas_and_orm_mapping(self):
        """Verify Pydantic schemas validate types, units, and convert ORM models cleanly."""
        # Valid Farmer schema
        farmer_data = FarmerCreate(name="Anil Borse", phone="+919876543210")
        farmer = Farmer(**farmer_data.model_dump())
        self.db.add(farmer)
        self.db.commit()
        self.db.refresh(farmer)

        farmer_resp = FarmerResponse.model_validate(farmer)
        self.assertEqual(farmer_resp.id, farmer.id)
        self.assertEqual(farmer_resp.name, "Anil Borse")

        # Invalid Farm area (must be > 0)
        with self.assertRaises(ValidationError):
            FarmCreate(farmer_id=farmer.id, name="Bad Farm", location="Dhule", area=-5.0, area_unit=AreaUnit.ACRE)

        # Invalid area unit (only acre or hectare allowed)
        with self.assertRaises(ValidationError):
            FarmCreate(farmer_id=farmer.id, name="Bad Farm", location="Dhule", area=2.0, area_unit="bigha")

        # Valid Farm schema
        farm_data = FarmCreate(farmer_id=farmer.id, name="Valid Farm", location="Dhule", area=3.5, area_unit=AreaUnit.HECTARE)
        farm = Farm(**farm_data.model_dump())
        self.db.add(farm)
        self.db.commit()
        self.db.refresh(farm)

        farm_resp = FarmResponse.model_validate(farm)
        self.assertEqual(farm_resp.area, 3.5)
        self.assertEqual(farm_resp.area_unit, "hectare")

        # Valid Crop schema
        crop_data = CropCreate(
            farm_id=farm.id,
            crop_name="Onion",
            variety="Garva",
            sowing_date=date(2026, 7, 1),
            area=3.5,
            area_unit=AreaUnit.HECTARE,
        )
        crop = Crop(**crop_data.model_dump())
        self.db.add(crop)
        self.db.commit()
        self.db.refresh(crop)

        crop_resp = CropResponse.model_validate(crop)
        self.assertEqual(crop_resp.crop_name, "Onion")
        self.assertEqual(crop_resp.variety, "Garva")
        self.assertIsNone(crop_resp.expected_harvest_date)


if __name__ == "__main__":
    unittest.main()
