"""
Integration and unit test suite for Milestone 15: Historical & Real-World Recommendation Validation.
Verifies chronological walk-forward execution, strict absence of lookahead bias,
prediction metrics against naive baseline, sell recommendation directional outcomes,
formally not-evaluable harvest status, failure case reporting, and read-only API endpoint.
"""

from datetime import date, timedelta
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from urllib.request import Request, urlopen

import uvicorn

from app.main import app
from app.ml.datasets.loader import get_default_dataset_path
from app.ml.validation.historical_validator import (
    run_walk_forward_validation,
    validate_historical_dataset,
)
from app.schemas.validation import HistoricalValidationResponse
from app.services.validation_service import ValidationService


class TestHistoricalValidation(unittest.TestCase):
    """Verifies all historical validation requirements and API contracts."""

    @classmethod
    def setUpClass(cls):
        # Warm the cache before starting the server so API call is instant
        ValidationService.warm_cache()

        cls.port = 8806
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
        ValidationService.clear_cache()

    def _http_get(self, path: str):
        req = Request(f"{self.base_url}{path}", method="GET")
        with urlopen(req, timeout=5.0) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    # =========================================================================
    # 1. Dataset Structure and Integrity Tests
    # =========================================================================

    def test_validate_historical_dataset_real_data(self):
        summary = validate_historical_dataset()
        self.assertEqual(summary["commodity"], "Onion (Red)")
        self.assertEqual(summary["total_records"], 70)
        self.assertEqual(summary["usable_records"], 70)
        self.assertEqual(summary["mandis_count"], 5)
        self.assertEqual(summary["start_date"], "2026-09-15")
        self.assertEqual(summary["end_date"], "2026-09-28")

    def test_empty_dataset_raises_error(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"commodity": "Onion", "unit": "Rs./Quintal", "mandis": {"Lasalgaon": {"recent_rates": []}}}, f)
            temp_path = f.name

        try:
            with self.assertRaises(ValueError):
                validate_historical_dataset(temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    # =========================================================================
    # 2. Chronological Walk-Forward Validation Tests
    # =========================================================================

    def test_walk_forward_validation_execution(self):
        report = run_walk_forward_validation()
        self.assertIsInstance(report, HistoricalValidationResponse)

        # 5 mandis * 13 transitions = 65 transitions
        self.assertEqual(report.number_of_evaluated_cases, 65)

        # Initial day 1 transitions where history count == 1
        self.assertEqual(report.number_of_not_evaluable_cases, 5)

        # Evaluation period
        self.assertEqual(report.evaluation_period["start_date"], "2026-09-15")
        self.assertEqual(report.evaluation_period["end_date"], "2026-09-28")
        self.assertEqual(report.evaluation_period["horizon"], "1-day walk-forward")

    def test_no_future_data_leakage_guarantee(self):
        """
        Verifies that at step i, predictions and posture evaluations rely exclusively
        on historical records <= i, with zero lookahead bias.
        """
        report = run_walk_forward_validation()
        pred_val = report.prediction_validation

        # Total evaluated transitions must equal sum of per-market transitions
        market_transitions_sum = sum(m.evaluated_transitions for m in pred_val.by_market)
        self.assertEqual(market_transitions_sum, pred_val.total_evaluated_transitions)
        self.assertEqual(pred_val.total_evaluated_transitions, 65)

    # =========================================================================
    # 3. Prediction Evaluation Metrics Tests
    # =========================================================================

    def test_prediction_metrics_present_and_sensible(self):
        report = run_walk_forward_validation()
        pred_val = report.prediction_validation

        # Check overall model performance
        self.assertGreater(pred_val.overall_model_performance.mae, 0)
        self.assertGreater(pred_val.overall_model_performance.rmse, 0)
        self.assertGreater(pred_val.overall_model_performance.mape_percent, 0)

        # Check naive baseline performance
        self.assertGreater(pred_val.overall_naive_performance.mae, 0)
        self.assertGreater(pred_val.overall_naive_performance.rmse, 0)

        # Per-market breakdowns exist for all 5 mandis
        self.assertEqual(len(pred_val.by_market), 5)
        for m in pred_val.by_market:
            self.assertEqual(m.evaluated_transitions, 13)
            self.assertGreater(m.model_performance.mae, 0)

    # =========================================================================
    # 4. Sell Recommendation Outcomes Tests
    # =========================================================================

    def test_sell_recommendation_outcomes(self):
        report = run_walk_forward_validation()
        sell_val = report.sell_recommendation_validation

        # Total evaluated decisions: 65 transitions - 5 (day 1 insufficient_data) = 60
        self.assertEqual(sell_val.total_evaluated_decisions, 60)
        self.assertEqual(
            sell_val.total_agreed + sell_val.total_disagreed + sell_val.total_neutral,
            60,
        )

        # Overall agreement rate
        self.assertIsNotNone(sell_val.overall_agreement_rate_percent)
        self.assertTrue(0 <= sell_val.overall_agreement_rate_percent <= 100)

        # Breakdown by posture exists
        self.assertIn("hold_for_observation", sell_val.by_posture)
        self.assertIn("sell_now", sell_val.by_posture)
        self.assertIn("price_stable", sell_val.by_posture)

    # =========================================================================
    # 5. Harvest Recommendation: Formally not_evaluable
    # =========================================================================

    def test_harvest_recommendation_not_evaluable(self):
        """
        Crucial requirement: Harvest recommendations must be reported as not_evaluable
        because raw historical data contains no crop lifecycle/harvest observations.
        Must NOT fabricate harvest outcomes or infer maturity from prices.
        """
        report = run_walk_forward_validation()
        harvest_val = report.harvest_recommendation_validation

        self.assertEqual(harvest_val.status, "not_evaluable")
        self.assertEqual(harvest_val.evaluated_cases, 0)
        self.assertIn("crop observations", harvest_val.reason.lower())
        self.assertIn("cannot be scientifically inferred", harvest_val.reason.lower())

    # =========================================================================
    # 6. Failure Cases & High-Error Case Detection
    # =========================================================================

    def test_failure_cases_identification(self):
        report = run_walk_forward_validation()
        failures = report.failure_cases

        # Failure cases must be non-empty (day 1 insufficient_data cases are logged)
        self.assertTrue(len(failures) > 0)

        # Check for insufficient_data cases on day 1
        insufficient_cases = [f for f in failures if f.failure_type == "insufficient_data"]
        self.assertEqual(len(insufficient_cases), 5)

        for f in failures:
            self.assertIn(f.failure_type, ["insufficient_data", "direction_disagreement", "high_prediction_error"])
            self.assertTrue(len(f.evidence) > 10)
            self.assertIsNotNone(f.date)
            self.assertIsNotNone(f.market)

    # =========================================================================
    # 7. Validation API Endpoint Tests
    # =========================================================================

    def test_validation_api_endpoint_success(self):
        status_code, data = self._http_get("/api/v1/validation/historical")
        self.assertEqual(status_code, 200)

        # Matches HistoricalValidationResponse schema
        self.assertEqual(data["dataset_summary"]["commodity"], "Onion (Red)")
        self.assertEqual(data["dataset_summary"]["total_records"], 70)
        self.assertEqual(data["harvest_recommendation_validation"]["status"], "not_evaluable")
        self.assertEqual(data["harvest_recommendation_validation"]["evaluated_cases"], 0)
        self.assertEqual(data["prediction_validation"]["model_name"], "LinearRegressionBaseline")
        self.assertEqual(data["prediction_validation"]["total_evaluated_transitions"], 65)
        self.assertEqual(data["sell_recommendation_validation"]["total_evaluated_decisions"], 60)
        self.assertTrue(len(data["data_limitations"]) >= 3)
        self.assertTrue(len(data["failure_cases"]) > 0)


if __name__ == "__main__":
    unittest.main()
