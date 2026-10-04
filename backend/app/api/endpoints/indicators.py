"""
REST API endpoints for Agricultural Decision-Ready Indicators.
Provides deterministic, read-only analytics for crops, farm weather, and mandi markets.
Does NOT execute predictions, machine learning, or harvest/sell recommendations.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.indicators import (
    CropIndicatorsResponse,
    WeatherIndicatorsResponse,
    MarketIndicatorsResponse,
)
from app.services.crop_indicator_service import CropIndicatorService
from app.services.weather_indicator_service import WeatherIndicatorService
from app.services.market_indicator_service import MarketIndicatorService

router = APIRouter(tags=["Agricultural Indicators"])


@router.get(
    "/crops/{crop_id}/indicators",
    response_model=CropIndicatorsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Crop Indicators",
    description="Calculates deterministic indicators for a crop planting from recorded field observations.",
)
def get_crop_indicators(
    crop_id: int,
    db: Session = Depends(get_db),
) -> CropIndicatorsResponse:
    service = CropIndicatorService(db)
    return service.get_crop_indicators(crop_id)


@router.get(
    "/farms/{farm_id}/weather-indicators",
    response_model=WeatherIndicatorsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Farm Weather Indicators",
    description="Calculates deterministic statistical indicators from recorded farm weather measurements.",
)
def get_farm_weather_indicators(
    farm_id: int,
    db: Session = Depends(get_db),
) -> WeatherIndicatorsResponse:
    service = WeatherIndicatorService(db)
    return service.get_farm_weather_indicators(farm_id)


@router.get(
    "/market-indicators",
    response_model=MarketIndicatorsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Mandi Market Indicators",
    description="Calculates summary statistics and price momentum for a crop/market combination.",
)
def get_market_indicators(
    crop_name: Optional[str] = Query(None, description="Optional commodity/crop filter"),
    market_name: Optional[str] = Query(None, description="Optional APMC mandi market filter"),
    db: Session = Depends(get_db),
) -> MarketIndicatorsResponse:
    service = MarketIndicatorService(db)
    return service.get_market_indicators(crop_name=crop_name, market_name=market_name)
