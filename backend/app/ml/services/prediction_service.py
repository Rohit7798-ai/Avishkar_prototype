"""
Market Price Prediction Service.
Coordinates feature validation, model inference, and training pipeline execution.
Contains NO recommendation logic; strictly outputs transparent numeric predictions.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from app.ml.datasets.loader import get_default_dataset_path, load_raw_mandi_dataset
from app.ml.evaluation.metrics import evaluate_pipeline
from app.ml.features.preparation import (
    prepare_market_price_features,
    split_train_validation_chronological,
)
from app.ml.models.linear_regression import LinearRegressionBaseline


def get_default_model_artifact_path() -> Path:
    """Returns absolute path to stored baseline model artifact."""
    current_dir = Path(__file__).resolve().parent
    # ml/services -> ml -> app -> backend -> root
    project_root = current_dir.parent.parent.parent.parent
    return project_root / "data" / "processed" / "market_price_baseline_model.json"


class MarketPricePredictionService:
    """Inference and training orchestration service for market price forecasting."""

    def __init__(
        self,
        model_artifact_path: Optional[str | Path] = None,
        auto_train_if_missing: bool = True,
    ):
        self.artifact_path = Path(model_artifact_path) if model_artifact_path else get_default_model_artifact_path()
        self.model: Optional[LinearRegressionBaseline] = None

        if self.artifact_path.exists():
            try:
                self.model = LinearRegressionBaseline.load(self.artifact_path)
            except Exception:
                self.model = None

        if self.model is None and auto_train_if_missing:
            self.train_and_save()

    def train_and_save(
        self,
        dataset_path: Optional[str | Path] = None,
        split_ratio: float = 0.75,
    ) -> Dict[str, Any]:
        """
        Loads historical dataset, splits chronologically, trains baseline model,
        evaluates against naive baseline, and saves model artifact.

        Returns:
            Dict containing evaluation report.
        """
        records = load_raw_mandi_dataset(dataset_path or get_default_dataset_path())
        samples = prepare_market_price_features(records)

        if len(samples) < 5:
            raise ValueError(f"Insufficient historical samples to train model: {len(samples)}.")

        train_samples, val_samples = split_train_validation_chronological(samples, split_ratio=split_ratio)

        model = LinearRegressionBaseline()
        model.fit(train_samples)

        # Save model artifact
        self.artifact_path.parent.mkdir(parents=True, exist_ok=True)
        model.save(self.artifact_path)
        self.model = model

        # Evaluate model
        evaluation_report = evaluate_pipeline(train_samples, val_samples, model)
        return evaluation_report

    def predict_next_day_price(
        self,
        current_modal_price: float,
        price_spread: float = 0.0,
        arrivals_tonnes: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Generates a next-day modal price prediction for given market features.

        Args:
            current_modal_price: Today's modal mandi price quote (must be > 0).
            price_spread: Intraday spread (max_price - min_price) (>= 0).
            arrivals_tonnes: Daily market arrival volume in tonnes (>= 0).

        Returns:
            Dict containing prediction, model metadata, and inputs used.
        """
        if current_modal_price <= 0:
            raise ValueError("current_modal_price must be strictly positive.")
        if price_spread < 0:
            raise ValueError("price_spread cannot be negative.")
        if arrivals_tonnes < 0:
            raise ValueError("arrivals_tonnes cannot be negative.")

        if self.model is None or not self.model.is_fitted:
            raise RuntimeError("Prediction model is not trained or loaded.")

        predicted_val = self.model.predict_one(
            current_modal_price=current_modal_price,
            price_spread=price_spread,
            arrivals_tonnes=arrivals_tonnes,
        )

        return {
            "predicted_next_modal_price": predicted_val,
            "currency": "Rs/Quintal",
            "model_name": self.model.model_name,
            "model_version": self.model.model_version,
            "features_used": {
                "current_modal_price": current_modal_price,
                "price_spread": price_spread,
                "arrivals_tonnes": arrivals_tonnes,
            },
            "predicted_at": datetime.utcnow().isoformat(),
        }
