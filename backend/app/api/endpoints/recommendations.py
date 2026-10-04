"""
REST API endpoints for the Harvest & Sell Recommendation Engine.
Provides transparent, deterministic recommendations grounded strictly in
field observations, farm weather indicators, mandi price movements, and baseline ML forecasts.
Keeps harvest and sell recommendations completely decoupled.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.recommendation import CropRecommendationResponse
from app.services.recommendation_service import RecommendationService

router = APIRouter(tags=["Recommendations"])


@router.get(
    "/crops/{crop_id}/recommendation",
    response_model=CropRecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Crop Harvest & Sell Recommendations",
    description=(
        "Evaluates transparent, decoupled harvest and selling recommendations for a crop planting. "
        "Every recommendation is accompanied by explicit supporting factors, reasons, risks, "
        "and data quality metrics without black-box scores."
    ),
)
def get_crop_recommendation(
    crop_id: int,
    db: Session = Depends(get_db),
) -> CropRecommendationResponse:
    """
    Returns decoupled harvest and selling recommendations for the specified crop planting.
    """
    service = RecommendationService(db)
    return service.get_crop_recommendation(crop_id)
