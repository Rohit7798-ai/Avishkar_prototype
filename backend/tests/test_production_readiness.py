"""
Unit tests for production readiness, health probes, readiness probes,
error hardening, and environment configuration.
"""

import unittest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.session import engine, get_db
from app.main import app, create_application


class TestProductionReadiness(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_check_endpoint(self):
        """Verify GET /api/health returns operational status without touching DB."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(data.get("service"), "farmer-decision-system")

    def test_readiness_probe_healthy(self):
        """Verify GET /api/ready returns 200 and 'ready' status when DB is connected."""
        response = self.client.get("/api/ready")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "ready")
        self.assertEqual(data.get("database"), "connected")
        self.assertIn("environment", data)

    def test_readiness_probe_database_failure(self):
        """Verify GET /api/ready returns 503 and 'unavailable' status when DB probe fails."""
        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("Database connection refused")

        def override_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db
        try:
            response = self.client.get("/api/ready")
            self.assertEqual(response.status_code, 503)
            data = response.json()
            self.assertEqual(data.get("status"), "unavailable")
            self.assertEqual(data.get("database"), "disconnected")
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_unhandled_exception_handler(self):
        """Verify that an unhandled internal exception returns clean 500 without stack trace leaks."""
        test_app = create_application()

        @test_app.get("/api/test-crash")
        def crash_route():
            raise RuntimeError("Database connection string leaked: secret_password_123")

        crash_client = TestClient(test_app, raise_server_exceptions=False)
        response = crash_client.get("/api/test-crash")

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertEqual(data, {"detail": "Internal server error"})
        # Verify no secret leaked in response
        self.assertNotIn("secret_password_123", response.text)
        self.assertNotIn("RuntimeError", response.text)
        self.assertNotIn("Traceback", response.text)

    def test_settings_cors_parsing(self):
        """Verify CORS settings properly parse comma-separated and JSON string formats."""
        s1 = Settings(BACKEND_CORS_ORIGINS="http://example.com, https://app.example.com")
        self.assertEqual(s1.BACKEND_CORS_ORIGINS, ["http://example.com", "https://app.example.com"])

        s2 = Settings(BACKEND_CORS_ORIGINS='["http://foo.com", "http://bar.com"]')
        self.assertEqual(s2.BACKEND_CORS_ORIGINS, ["http://foo.com", "http://bar.com"])

    def test_engine_pool_pre_ping(self):
        """Verify SQLAlchemy engine has pool_pre_ping enabled for production database resilience."""
        self.assertTrue(engine.pool._pre_ping)


if __name__ == "__main__":
    unittest.main()
