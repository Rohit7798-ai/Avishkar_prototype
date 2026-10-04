"""
Pydantic schemas for Agricultural Decision-Ready Indicators.
Supports Crop, Weather, and Market indicators computed deterministically
from empirical database observations without external API calls or AI/ML.
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class CropIndicatorsResponse(BaseModel):
    """
    Structured crop indicators computed from recorded field observations.
    All fields are either observed facts or deterministic calculations.
    """
    model_config = ConfigDict(from_attributes=True)

    crop_id: int
    latest_growth_stage: Optional[str] = None
    latest_health_status: Optional[str] = None
    latest_observation_date: Optional[date] = None
    observation_count: int = 0
    number_of_observations: int = 0
    days_since_latest_observation: Optional[int] = None


class WeatherIndicatorsResponse(BaseModel):
    """
    Structured farm weather indicators computed from recorded weather measurements.
    All fields are empirical observations or statistical aggregations.
    """
    model_config = ConfigDict(from_attributes=True)

    farm_id: int
    latest_temperature: Optional[float] = None
    latest_humidity: Optional[float] = None
    latest_rainfall: Optional[float] = None
    latest_wind_speed: Optional[float] = None
    latest_observed_at: Optional[datetime] = None
    latest_observation_timestamp: Optional[datetime] = None
    observation_count: int = 0
    number_of_observations: int = 0
    average_temperature: Optional[float] = None
    total_rainfall: Optional[float] = None
    average_humidity: Optional[float] = None
    average_wind_speed: Optional[float] = None


class MarketIndicatorsResponse(BaseModel):
    """
    Structured mandi market indicators computed from recorded price observations.
    Provides latest, range, summary stats and price momentum without future predictions.
    """
    model_config = ConfigDict(from_attributes=True)

    crop_name: Optional[str] = None
    market_name: Optional[str] = None
    latest_price: Optional[float] = None
    earliest_price: Optional[float] = None
    highest_price: Optional[float] = None
    lowest_price: Optional[float] = None
    average_price: Optional[float] = None
    observation_count: int = 0
    number_of_observations: int = 0
    latest_observation_date: Optional[date] = None
    price_change: Optional[float] = None
    price_change_percentage: Optional[float] = None
