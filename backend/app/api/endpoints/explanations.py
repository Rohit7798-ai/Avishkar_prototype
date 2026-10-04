"""
REST API endpoints for the AI Explanation Layer.
Provides transparent, farmer-friendly explanations translating domain indicators,
decision engine assessments, and baseline price predictions into plain-language insights.
Contains zero recommendations, zero speculative advice, and zero fake data.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.explanation import CropExplanationResponse
from app.services.explanation_service import ExplanationService

router = APIRouter(tags=["AI Explanations"])


@router.get(
    "/crops/{crop_id}/explanation",
    response_model=CropExplanationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Farmer-Friendly Crop Explanation",
    description=(
        "Synthesizes crop observations, farm weather indicators, mandi market trends, "
        "decision engine assessments, and baseline price predictions into clear, explainable insights. "
        "Strictly categorizes data into Observed, Calculated, Predicted, and Assessment categories."
    ),
)
def get_crop_explanation(
    crop_id: int,
    db: Session = Depends(get_db),
) -> CropExplanationResponse:
    """
    Returns an explainable, farmer-friendly breakdown for the specified crop planting.
    """
    service = ExplanationService(db)
    return service.get_crop_explanation(crop_id)
