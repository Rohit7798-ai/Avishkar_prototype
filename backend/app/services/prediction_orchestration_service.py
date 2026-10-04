"""
Domain orchestration service connecting API layer to ML prediction pipeline.
Maintains architectural boundary: API -> Service -> ML Service -> Model.
Does NOT implement recommendations; pure prediction evaluation.
"""

from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleViolationException
from app.ml.services.prediction_service import MarketPricePredictionService
from app.schemas.prediction import MarketPricePredictionRequest


class PredictionOrchestrationService:
    """Coordinates prediction requests and evaluation reporting for domain consumers."""

    def __init__(
        self,
        db: Optional[Session] = None,
        ml_service: Optional[MarketPricePredictionService] = None,
    ):
        self.db = db
        self.ml_service = ml_service or MarketPricePredictionService()

    def predict_market_price(self, request: MarketPricePredictionRequest) -> Dict[str, Any]:
        """
        Validates business parameters and invokes the underlying baseline model.
        """
        crop = request.crop_name or "Onion (Red)"
        market = request.market_name

        try:
            prediction_result = self.ml_service.predict_next_day_price(
                current_modal_price=request.current_modal_price,
                price_spread=request.price_spread or 0.0,
                arrivals_tonnes=request.arrivals_tonnes or 0.0,
            )
        except ValueError as exc:
            raise BusinessRuleViolationException(str(exc)) from exc
        except RuntimeError as exc:
            raise BusinessRuleViolationException(f"Prediction model error: {exc}") from exc

        return {
            "crop_name": crop,
            "market_name": market,
            "predicted_next_modal_price": prediction_result["predicted_next_modal_price"],
            "currency": prediction_result["currency"],
            "model_name": prediction_result["model_name"],
            "model_version": prediction_result["model_version"],
            "features_used": prediction_result["features_used"],
            "predicted_at": prediction_result["predicted_at"],
        }

    def get_model_evaluation(self) -> Dict[str, Any]:
        """
        Executes and returns the baseline evaluation report comparing against naive persistence.
        """
        try:
            return self.ml_service.train_and_save()
        except Exception as exc:
            raise BusinessRuleViolationException(f"Failed to generate model evaluation: {exc}") from exc
