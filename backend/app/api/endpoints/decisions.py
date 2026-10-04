"""
REST API endpoints for Transparent Agricultural Decision Assessments.
Provides deterministic, explainable condition evaluations for harvest and mandi markets.
Does NOT predict future dates, future prices, or recommend actions.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.decision import (
    HarvestAssessmentResponse,
    MarketAssessmentResponse,
)
from app.services.decision_engine_service import DecisionEngineService

router = APIRouter(tags=["Decision Assessments"])


@router.get(
    "/crops/{crop_id}/decision-assessment",
    response_model=HarvestAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Crop Harvest Assessment",
    description="Evaluates deterministic crop and farm weather indicators for harvest readiness without predictions.",
)
def get_crop_decision_assessment(
    crop_id: int,
    db: Session = Depends(get_db),
) -> HarvestAssessmentResponse:
    service = DecisionEngineService(db)
    return service.evaluate_harvest_assessment(crop_id)


@router.get(
    "/market-decision-assessment",
    response_model=MarketAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Market Decision Assessment",
    description="Evaluates empirical mandi price movements and trend stability without predicting future prices.",
)
def get_market_decision_assessment(
    crop_name: Optional[str] = Query(None, description="Optional commodity/crop filter"),
    market_name: Optional[str] = Query(None, description="Optional APMC mandi market filter"),
    db: Session = Depends(get_db),
) -> MarketAssessmentResponse:
    service = DecisionEngineService(db)
    return service.evaluate_market_assessment(crop_name=crop_name, market_name=market_name)
