"""
Unit and integration test suite for Milestone 12: Machine Learning Prediction Pipeline.
Tests historical dataset loading, validation, feature engineering, chronological splitting,
baseline models, evaluation metrics, and prediction services.
"""

from datetime import date, timedelta
import json
from pathlib import Path
import tempfile
import unittest

from fastapi import HTTPException

from app.api.endpoints.predictions import get_model_evaluation, predict_market_price
from app.ml.datasets.loader import get_default_dataset_path, load_raw_mandi_dataset
from app.ml.evaluation.metrics import calculate_regression_metrics, evaluate_pipeline
from app.ml.features.preparation import (
    prepare_market_price_features,
    split_train_validation_chronological,
)
from app.ml.models.baseline import NaivePersistenceModel
from app.ml.models.linear_regression import LinearRegressionBaseline
from app.ml.services.prediction_service import MarketPricePredictionService
from app.schemas.prediction import MarketPricePredictionRequest


class TestMLPipeline(unittest.TestCase):
    """Automated test suite for historical data processing and prediction baseline."""

    def setUp(self):
        self.dataset_path = get_default_dataset_path()

    # =========================================================================
    # 1. Dataset Loading and Validation Tests
    # =========================================================================

    def test_load_real_raw_dataset_success(self):
        records = load_raw_mandi_dataset(self.dataset_path)
        self.assertEqual(len(records), 70)  # 5 mandis * 14 days
        sample = records[0]
        self.assertIn("market", sample)
        self.assertIn("date", sample)
        self.assertIn("modal_price", sample)
        self.assertIn("min_price", sample)
        self.assertIn("max_price", sample)
        self.assertIn("arrivals_tonnes", sample)
        self.assertTrue(sample["min_price"] <= sample["modal_price"] <= sample["max_price"])
        self.assertTrue(isinstance(sample["date"], date))

    def test_loader_missing_file_raises_not_found(self):
        with self.assertRaises(FileNotFoundError):
            load_raw_mandi_dataset("non_existent_path.json")

    def test_loader_missing_columns_raises_error(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"commodity": "Onion"}, f)
            temp_path = f.name

        try:
            with self.assertRaises(ValueError) as ctx:
                load_raw_mandi_dataset(temp_path)
            self.assertIn("Missing required top-level attribute", str(ctx.exception))
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_loader_inconsistent_prices_raises_error(self):
        bad_data = {
            "commodity": "Onion",
            "unit": "Rs./Quintal",
            "mandis": {
                "Lasalgaon": {
                    "district": "Nashik",
                    "distance_km_nashik": 50,
                    "recent_rates": [
                        {"date": "2026-09-15", "min": 2500, "modal": 2100, "max": 2000, "arrivals_tonnes": 500}
                    ],
                }
            },
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(bad_data, f)
            temp_path = f.name

        try:
            with self.assertRaises(ValueError) as ctx:
                load_raw_mandi_dataset(temp_path)
            self.assertIn("Price consistency violation", str(ctx.exception))
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_loader_duplicate_records_deduplicated(self):
        dup_data = {
            "commodity": "Onion",
            "unit": "Rs./Quintal",
            "mandis": {
                "Lasalgaon": {
                    "district": "Nashik",
                    "distance_km_nashik": 50,
                    "recent_rates": [
                        {"date": "2026-09-15", "min": 1800, "modal": 2100, "max": 2400, "arrivals_tonnes": 500},
                        {"date": "2026-09-15", "min": 1800, "modal": 2100, "max": 2400, "arrivals_tonnes": 500},  # Duplicate
                    ],
                }
            },
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(dup_data, f)
            temp_path = f.name

        try:
            records = load_raw_mandi_dataset(temp_path)
            self.assertEqual(len(records), 1)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    # =========================================================================
    # 2. Feature Preparation & Leakage Protection Tests
    # =========================================================================

    def test_feature_preparation_construction(self):
        records = load_raw_mandi_dataset(self.dataset_path)
        samples = prepare_market_price_features(records)

        # 5 mandis with 14 daily quotes -> 13 (t, t+1) pairs per mandi = 65 total pairs
        self.assertEqual(len(samples), 65)

        first = samples[0]
        self.assertIn("current_modal_price", first)
        self.assertIn("price_spread", first)
        self.assertIn("arrivals_tonnes", first)
        self.assertIn("day_of_week", first)
        self.assertIn("target_next_modal_price", first)
        self.assertEqual(first["next_date"] - first["date"], timedelta(days=1))

    def test_feature_preparation_skips_calendar_gaps(self):
        gap_records = [
            {"market": "Lasalgaon", "date": date(2026, 9, 15), "min_price": 1800, "modal_price": 2000, "max_price": 2200, "arrivals_tonnes": 500},
            {"market": "Lasalgaon", "date": date(2026, 9, 20), "min_price": 1900, "modal_price": 2100, "max_price": 2300, "arrivals_tonnes": 400},  # 5-day gap
        ]
        samples = prepare_market_price_features(gap_records)
        self.assertEqual(len(samples), 0)

    # =========================================================================
    # 3. Chronological Train/Validation Split Tests
    # =========================================================================

    def test_chronological_split_strict_temporal_boundary(self):
        records = load_raw_mandi_dataset(self.dataset_path)
        samples = prepare_market_price_features(records)
        train_samples, val_samples = split_train_validation_chronological(samples, split_ratio=0.75)

        self.assertGreater(len(train_samples), 0)
        self.assertGreater(len(val_samples), 0)
        self.assertEqual(len(train_samples) + len(val_samples), len(samples))

        max_train_date = max(s["date"] for s in train_samples)
        min_val_date = min(s["date"] for s in val_samples)

        # Strict chronological order: No future records in training data
        self.assertLess(max_train_date, min_val_date)

    # =========================================================================
    # 4. Baseline Models & Evaluation Metrics Tests
    # =========================================================================

    def test_naive_persistence_baseline(self):
        model = NaivePersistenceModel()
        self.assertEqual(model.predict_one(current_modal_price=2200.0), 2200.0)
        preds = model.predict([{"current_modal_price": 2100}, {"current_modal_price": 2300}])
        self.assertEqual(preds, [2100.0, 2300.0])

    def test_linear_regression_training_and_serialization(self):
        records = load_raw_mandi_dataset(self.dataset_path)
        samples = prepare_market_price_features(records)
        train, val = split_train_validation_chronological(samples, split_ratio=0.75)

        model = LinearRegressionBaseline()
        model.fit(train)

        self.assertTrue(model.is_fitted)
        self.assertEqual(len(model.coefficients), 3)

        pred = model.predict_one(current_modal_price=2200.0, price_spread=400.0, arrivals_tonnes=1200.0)
        self.assertIsInstance(pred, float)
        self.assertGreater(pred, 0.0)

        # Persistence roundtrip test
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name
        try:
            model.save(temp_path)
            loaded = LinearRegressionBaseline.load(temp_path)
            self.assertEqual(loaded.coefficients, model.coefficients)
            self.assertEqual(loaded.intercept, model.intercept)
            loaded_pred = loaded.predict_one(current_modal_price=2200.0, price_spread=400.0, arrivals_tonnes=1200.0)
            self.assertEqual(loaded_pred, pred)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_regression_metrics_calculation(self):
        y_true = [100.0, 200.0, 300.0]
        y_pred = [110.0, 190.0, 310.0]
        metrics = calculate_regression_metrics(y_true, y_pred)

        self.assertEqual(metrics["mae"], 10.0)
        self.assertEqual(metrics["rmse"], 10.0)
        self.assertAlmostEqual(metrics["r2"], 0.985, places=3)
        self.assertAlmostEqual(metrics["mape_percent"], 6.11, places=1)

    def test_pipeline_evaluation_report(self):
        records = load_raw_mandi_dataset(self.dataset_path)
        samples = prepare_market_price_features(records)
        train, val = split_train_validation_chronological(samples, split_ratio=0.75)

        model = LinearRegressionBaseline().fit(train)
        report = evaluate_pipeline(train, val, model)

        self.assertIn("training_period", report)
        self.assertIn("validation_period", report)
        self.assertIn("model_performance", report)
        self.assertIn("naive_baseline_performance", report)
        self.assertIn("mae_improvement_percent", report)
        self.assertGreater(report["model_performance"]["r2"], 0.0)

    # =========================================================================
    # 5. Prediction Service & Endpoint Direct Calls
    # =========================================================================

    def test_prediction_service_workflow(self):
        service = MarketPricePredictionService()
        result = service.predict_next_day_price(
            current_modal_price=2300.0,
            price_spread=350.0,
            arrivals_tonnes=1100.0,
        )
        self.assertIn("predicted_next_modal_price", result)
        self.assertEqual(result["currency"], "Rs/Quintal")
        self.assertEqual(result["model_name"], "linear_regression_baseline")
        self.assertEqual(result["model_version"], "1.0.0")

    def test_prediction_api_endpoints_direct(self):
        req = MarketPricePredictionRequest(
            crop_name="Onion (Red)",
            market_name="Lasalgaon",
            current_modal_price=2400.0,
            price_spread=420.0,
            arrivals_tonnes=1250.0,
        )
        resp = predict_market_price(req)
        self.assertGreater(resp.predicted_next_modal_price, 0.0)
        self.assertEqual(resp.crop_name, "Onion (Red)")

        # Invalid price raises 400
        with self.assertRaises(HTTPException) as ctx:
            bad_req = MarketPricePredictionRequest.model_construct(
                crop_name="Onion (Red)",
                current_modal_price=-50.0,
                price_spread=0.0,
                arrivals_tonnes=0.0,
            )
            predict_market_price(bad_req)
        self.assertEqual(ctx.exception.status_code, 400)

        # Evaluation endpoint inspection
        eval_resp = get_model_evaluation()
        self.assertEqual(eval_resp.model_name, "linear_regression_baseline")
        self.assertGreater(eval_resp.training_period["record_count"], 0)
        self.assertGreater(eval_resp.validation_period["record_count"], 0)


if __name__ == "__main__":
    unittest.main()
