"""
Prediction API endpoints.
Provides baseline market price prediction and model evaluation inspection.
Architecture: API -> Service -> ML Service -> Model.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleViolationException
from app.db.session import get_db
from app.schemas.prediction import (
    MarketPricePredictionRequest,
    MarketPricePredictionResponse,
    ModelEvaluationSummaryResponse,
)
from app.services.prediction_orchestration_service import PredictionOrchestrationService

router = APIRouter(prefix="/predictions", tags=["Predictions"])


@router.post(
    "/market-price",
    response_model=MarketPricePredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate next-period modal market price prediction",
    description="Infers tomorrow's modal mandi rate using a trained linear regression baseline model.",
)
def predict_market_price(
    payload: MarketPricePredictionRequest,
    db: Session = Depends(get_db),
) -> MarketPricePredictionResponse:
    service = PredictionOrchestrationService(db)
    try:
        result = service.predict_market_price(payload)
        return MarketPricePredictionResponse(**result)
    except BusinessRuleViolationException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/market-price/evaluation",
    response_model=ModelEvaluationSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Inspect baseline model evaluation metrics",
    description="Returns training/validation period metrics (MAE, RMSE, R2) and comparison against naive persistence.",
)
def get_model_evaluation(
    db: Session = Depends(get_db),
) -> ModelEvaluationSummaryResponse:
    service = PredictionOrchestrationService(db)
    try:
        report = service.get_model_evaluation()
        return ModelEvaluationSummaryResponse(**report)
    except BusinessRuleViolationException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
