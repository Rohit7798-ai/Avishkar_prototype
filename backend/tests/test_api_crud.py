"""
Integration test suite for Farmer, Farm, and Crop CRUD API endpoints.
Tests complete HTTP lifecycle: Request -> Router -> Service -> Repository -> SQLite.
Uses an isolated in-memory test database and zero third-party testing dependencies.
"""

from datetime import date
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


class TestApiCrud(unittest.TestCase):
    """Verifies all required REST CRUD endpoints and validation constraints."""

    @classmethod
    def setUpClass(cls):
        # Configure dedicated isolated in-memory database with StaticPool so all threads share it
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

        # Override production get_db dependency
        app.dependency_overrides[get_db] = override_get_db

        # Launch test server on an isolated port
        cls.port = 8788
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

    # Helper HTTP request methods using standard library urllib
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
            try:
                data = json.loads(raw.decode("utf-8")) if raw and raw.strip() else None
            except Exception as err:
                raise RuntimeError(f"HTTPError {e.code}, raw content: {raw!r}") from err
            return e.code, data

    # =========================================================================
    # FARMER TESTS
    # =========================================================================

    def test_farmer_crud_lifecycle(self):
        # 1. Create farmer
        status_code, farmer = self._request("POST", "/api/v1/farmers", {"name": "Ramesh Patil", "phone": "+919823012345"})
        self.assertEqual(status_code, 201)
        self.assertEqual(farmer["name"], "Ramesh Patil")
        self.assertEqual(farmer["phone"], "+919823012345")
        farmer_id = farmer["id"]

        # 2. Retrieve farmer by ID
        status_code, fetched = self._request("GET", f"/api/v1/farmers/{farmer_id}")
        self.assertEqual(status_code, 200)
        self.assertEqual(fetched["id"], farmer_id)
        self.assertEqual(fetched["name"], "Ramesh Patil")

        # 3. List farmers
        status_code, farmers_list = self._request("GET", "/api/v1/farmers")
        self.assertEqual(status_code, 200)
        self.assertEqual(len(farmers_list), 1)

        # 4. Delete farmer
        status_code, _ = self._request("DELETE", f"/api/v1/farmers/{farmer_id}")
        self.assertEqual(status_code, 204)

        # 5. Missing farmer returns 404
        status_code, err = self._request("GET", f"/api/v1/farmers/{farmer_id}")
        self.assertEqual(status_code, 404)
        self.assertIn("not found", err["detail"])

    def test_missing_farmer_operations_return_404(self):
        status_code, _ = self._request("GET", "/api/v1/farmers/99999")
        self.assertEqual(status_code, 404)

        status_code, _ = self._request("DELETE", "/api/v1/farmers/99999")
        self.assertEqual(status_code, 404)

    # =========================================================================
    # FARM TESTS
    # =========================================================================

    def test_farm_crud_lifecycle(self):
        # Setup parent farmer
        _, farmer = self._request("POST", "/api/v1/farmers", {"name": "Suresh Shinde"})
        farmer_id = farmer["id"]

        # 1. Create farm for valid farmer
        status_code, farm = self._request("POST", "/api/v1/farms", {
            "farmer_id": farmer_id,
            "name": "Niphad North Parcel",
            "location": "Niphad, Nashik",
            "area": 4.5,
            "area_unit": "acre"
        })
        self.assertEqual(status_code, 201)
        self.assertEqual(farm["name"], "Niphad North Parcel")
        self.assertEqual(farm["area"], 4.5)
        farm_id = farm["id"]

        # 2. Retrieve farm
        status_code, fetched = self._request("GET", f"/api/v1/farms/{farm_id}")
        self.assertEqual(status_code, 200)
        self.assertEqual(fetched["id"], farm_id)

        # 3. List farms
        status_code, farms = self._request("GET", "/api/v1/farms")
        self.assertEqual(status_code, 200)
        self.assertEqual(len(farms), 1)

        # 4. Retrieve farms by farmer
        status_code, farmer_farms = self._request("GET", f"/api/v1/farmers/{farmer_id}/farms")
        self.assertEqual(status_code, 200)
        self.assertEqual(len(farmer_farms), 1)
        self.assertEqual(farmer_farms[0]["id"], farm_id)

        # 5. Delete farm
        status_code, _ = self._request("DELETE", f"/api/v1/farms/{farm_id}")
        self.assertEqual(status_code, 204)

        # 6. Missing farm returns 404
        status_code, _ = self._request("GET", f"/api/v1/farms/{farm_id}")
        self.assertEqual(status_code, 404)

    def test_reject_farm_for_nonexistent_farmer(self):
        status_code, err = self._request("POST", "/api/v1/farms", {
            "farmer_id": 99999,
            "name": "Orphan Field",
            "location": "Unknown",
            "area": 2.0,
            "area_unit": "acre"
        })
        self.assertEqual(status_code, 404)
        self.assertIn("Farmer with id 99999 not found", err["detail"])

    def test_missing_farm_operations_return_404(self):
        status_code, _ = self._request("GET", "/api/v1/farms/99999")
        self.assertEqual(status_code, 404)

        status_code, _ = self._request("DELETE", "/api/v1/farms/99999")
        self.assertEqual(status_code, 404)

        status_code, _ = self._request("GET", "/api/v1/farmers/99999/farms")
        self.assertEqual(status_code, 404)

    # =========================================================================
    # CROP TESTS
    # =========================================================================

    def test_crop_crud_lifecycle(self):
        # Setup parent farmer and farm
        _, farmer = self._request("POST", "/api/v1/farmers", {"name": "Ganesh Ghadge"})
        _, farm = self._request("POST", "/api/v1/farms", {
            "farmer_id": farmer["id"],
            "name": "Lasalgaon Field",
            "location": "Lasalgaon",
            "area": 5.0,
            "area_unit": "acre"
        })
        farm_id = farm["id"]

        # 1. Create crop for valid farm
        status_code, crop = self._request("POST", "/api/v1/crops", {
            "farm_id": farm_id,
            "crop_name": "Onion",
            "variety": "Bhima Super",
            "sowing_date": "2026-06-15",
            "expected_harvest_date": "2026-10-15",
            "area": 3.0,
            "area_unit": "acre"
        })
        self.assertEqual(status_code, 201)
        self.assertEqual(crop["crop_name"], "Onion")
        self.assertEqual(crop["sowing_date"], "2026-06-15")
        crop_id = crop["id"]

        # 2. Retrieve crop
        status_code, fetched = self._request("GET", f"/api/v1/crops/{crop_id}")
        self.assertEqual(status_code, 200)
        self.assertEqual(fetched["id"], crop_id)

        # 3. List crops
        status_code, crops = self._request("GET", "/api/v1/crops")
        self.assertEqual(status_code, 200)
        self.assertEqual(len(crops), 1)

        # 4. Retrieve crops by farm
        status_code, farm_crops = self._request("GET", f"/api/v1/farms/{farm_id}/crops")
        self.assertEqual(status_code, 200)
        self.assertEqual(len(farm_crops), 1)
        self.assertEqual(farm_crops[0]["id"], crop_id)

        # 5. Delete crop
        status_code, _ = self._request("DELETE", f"/api/v1/crops/{crop_id}")
        self.assertEqual(status_code, 204)

        # 6. Missing crop returns 404
        status_code, _ = self._request("GET", f"/api/v1/crops/{crop_id}")
        self.assertEqual(status_code, 404)

    def test_reject_crop_for_nonexistent_farm(self):
        status_code, err = self._request("POST", "/api/v1/crops", {
            "farm_id": 99999,
            "crop_name": "Onion",
            "sowing_date": "2026-07-01",
            "area": 2.0,
            "area_unit": "acre"
        })
        self.assertEqual(status_code, 404)
        self.assertIn("Farm with id 99999 not found", err["detail"])

    def test_missing_crop_operations_return_404(self):
        status_code, _ = self._request("GET", "/api/v1/crops/99999")
        self.assertEqual(status_code, 404)

        status_code, _ = self._request("DELETE", "/api/v1/crops/99999")
        self.assertEqual(status_code, 404)

        status_code, _ = self._request("GET", "/api/v1/farms/99999/crops")
        self.assertEqual(status_code, 404)

    # =========================================================================
    # VALIDATION TESTS
    # =========================================================================

    def test_reject_negative_or_zero_area(self):
        _, farmer = self._request("POST", "/api/v1/farmers", {"name": "Test Farmer"})
        farmer_id = farmer["id"]

        # Negative area for Farm
        status_code, _ = self._request("POST", "/api/v1/farms", {
            "farmer_id": farmer_id,
            "name": "Invalid Area Farm",
            "location": "Nashik",
            "area": -2.0,
            "area_unit": "acre"
        })
        self.assertEqual(status_code, 422)

        # Zero area for Farm
        status_code, _ = self._request("POST", "/api/v1/farms", {
            "farmer_id": farmer_id,
            "name": "Zero Area Farm",
            "location": "Nashik",
            "area": 0,
            "area_unit": "acre"
        })
        self.assertEqual(status_code, 422)

    def test_reject_invalid_area_unit(self):
        _, farmer = self._request("POST", "/api/v1/farmers", {"name": "Test Farmer"})
        farmer_id = farmer["id"]

        # Unsupported area unit
        status_code, _ = self._request("POST", "/api/v1/farms", {
            "farmer_id": farmer_id,
            "name": "Invalid Unit Farm",
            "location": "Nashik",
            "area": 2.5,
            "area_unit": "bigha"
        })
        self.assertEqual(status_code, 422)

    def test_reject_invalid_crop_dates(self):
        _, farmer = self._request("POST", "/api/v1/farmers", {"name": "Test Farmer"})
        _, farm = self._request("POST", "/api/v1/farms", {
            "farmer_id": farmer["id"],
            "name": "Valid Farm",
            "location": "Nashik",
            "area": 3.0,
            "area_unit": "acre"
        })

        # Expected harvest date earlier than sowing date
        status_code, err = self._request("POST", "/api/v1/crops", {
            "farm_id": farm["id"],
            "crop_name": "Onion",
            "sowing_date": "2026-08-01",
            "expected_harvest_date": "2026-07-01",  # Before sowing
            "area": 1.5,
            "area_unit": "acre"
        })
        self.assertEqual(status_code, 422)


if __name__ == "__main__":
    unittest.main()
