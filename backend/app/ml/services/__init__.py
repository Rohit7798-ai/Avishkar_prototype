"""
ML Services Package.
"""

from app.ml.services.prediction_service import (
    MarketPricePredictionService,
    get_default_model_artifact_path,
)

__all__ = [
    "MarketPricePredictionService",
    "get_default_model_artifact_path",
]
