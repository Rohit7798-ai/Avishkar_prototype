"""
Pydantic schemas for the Harvest and Sell Recommendation Engine.
Provides structured, transparent recommendations grounded strictly in
existing observations, indicators, decision engine assessments, and ML predictions.
Zero black-box scores, zero combined scores, zero guaranteed claims.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class HarvestRecommendation(BaseModel):
    """
    Transparent harvest recommendation for a crop planting.
    Evaluates physiological maturity and harvest readiness independently of market prices.
    """
    recommendation: str = Field(
        ...,
        description="Actionable status: harvest_now, approaching_harvest, not_ready, insufficient_data",
    )
    status: str = Field(..., description="Short condition label matching recommendation")
    confidence: str = Field(
        ...,
        description="Transparent confidence level: high, medium, low, insufficient",
    )
    reasons: List[str] = Field(
        ...,
        description="Explicit factual reasons explaining why this harvest recommendation was made",
    )
    supporting_factors: Dict[str, Any] = Field(
        ...,
        description="Grounded data points: growth_stage, health_status, days_since_observation, weather_available",
    )
    risks: List[str] = Field(
        default_factory=list,
        description="Identified agricultural or data-quality risks",
    )
    data_sufficiency: str = Field(
        ...,
        description="Data sufficiency evaluation: sufficient, partial, insufficient",
    )

    model_config = ConfigDict(extra="forbid")


class SellRecommendation(BaseModel):
    """
    Transparent selling recommendation for a crop commodity.
    Evaluates price momentum, trends, and baseline forecasts independently of harvest status.
    """
    recommendation: str = Field(
        ...,
        description="Actionable status: sell_now, hold_for_observation, price_stable, insufficient_data",
    )
    status: str = Field(..., description="Short market posture label matching recommendation")
    confidence: str = Field(
        ...,
        description="Transparent confidence level: high, medium, low, insufficient",
    )
    reasons: List[str] = Field(
        ...,
        description="Explicit market and trend reasons explaining why this selling recommendation was made",
    )
    supporting_factors: Dict[str, Any] = Field(
        ...,
        description="Grounded metrics: current_modal_price, price_change, trend_status, predicted_price, model_info",
    )
    risks: List[str] = Field(
        default_factory=list,
        description="Identified commercial, market volatility, or forecasting risks",
    )
    data_sufficiency: str = Field(
        ...,
        description="Market data sufficiency evaluation: sufficient, insufficient",
    )

    model_config = ConfigDict(extra="forbid")


class DataQualitySummary(BaseModel):
    """
    Transparent breakdown of data completeness, freshness, and input availability.
    """
    harvest_data_sufficiency: str
    market_data_sufficiency: str
    crop_observation_count: int
    observation_freshness_days: Optional[int] = None
    weather_observation_count: int
    market_observation_count: int
    prediction_available: bool

    model_config = ConfigDict(extra="forbid")


class CropRecommendationResponse(BaseModel):
    """
    Combined recommendation response presenting separate, decoupled
    Harvest and Sell decision outputs with full data traceability.
    """
    crop_id: int
    crop_name: str
    farm_name: str
    farm_location: str
    harvest_recommendation: HarvestRecommendation
    sell_recommendation: SellRecommendation
    data_quality: DataQualitySummary
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(extra="forbid")
