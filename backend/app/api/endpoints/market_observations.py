"""
REST API endpoints for MarketObservation entity.
Mounted under /api/v1.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.market_observation import MarketObservationCreate, MarketObservationResponse
from app.services.market_observation_service import MarketObservationService

router = APIRouter(tags=["Market Observations"])


@router.post(
    "/market-observations",
    response_model=MarketObservationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record Market Observation",
    description="Records an observed mandi price quote for a crop/commodity.",
)
def record_market_observation(
    payload: MarketObservationCreate,
    db: Session = Depends(get_db),
) -> MarketObservationResponse:
    service = MarketObservationService(db)
    obs = service.create_observation(payload)
    return MarketObservationResponse.model_validate(obs)


@router.get(
    "/market-observations",
    response_model=List[MarketObservationResponse],
    status_code=status.HTTP_200_OK,
    summary="List Market Observations",
    description="Retrieves recorded market price observations, optionally filtered by crop or market.",
)
def list_market_observations(
    crop_name: Optional[str] = Query(None, description="Filter by commodity/crop name"),
    market_name: Optional[str] = Query(None, description="Filter by APMC market name"),
    skip: int = Query(0, ge=0, description="Offset record count"),
    limit: int = Query(100, ge=1, le=1000, description="Page limit"),
    db: Session = Depends(get_db),
) -> List[MarketObservationResponse]:
    service = MarketObservationService(db)
    observations = service.get_observations(
        crop_name=crop_name,
        market_name=market_name,
        skip=skip,
        limit=limit,
    )
    return [MarketObservationResponse.model_validate(item) for item in observations]


@router.delete(
    "/market-observations/{observation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Market Observation",
    description="Deletes a specific market observation record.",
)
def delete_market_observation(
    observation_id: int,
    db: Session = Depends(get_db),
) -> Response:
    service = MarketObservationService(db)
    service.delete_observation(observation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
