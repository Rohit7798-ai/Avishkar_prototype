"""
Pydantic schemas for the AI / System Explanation Layer.
Provides transparent, farmer-friendly explanations grounded in observed, calculated,
predicted, and assessment data categories.
Zero recommendations, zero speculative advice.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ObservedDataBreakdown(BaseModel):
    """Categorized factual observations recorded by farmers or ambient sensors."""
    crop_stage: Optional[str] = None
    crop_health: Optional[str] = None
    latest_crop_observation_date: Optional[str] = None
    crop_observations_count: int = 0
    latest_weather: Optional[Dict[str, Any]] = None
    weather_observations_count: int = 0
    latest_market_price: Optional[float] = None
    latest_market_date: Optional[str] = None
    market_observations_count: int = 0

    model_config = ConfigDict(extra="forbid")


class CalculatedDataBreakdown(BaseModel):
    """Derived indicators computed deterministically from observations."""
    days_since_latest_crop_observation: Optional[int] = None
    average_temperature_c: Optional[float] = None
    total_rainfall_mm: Optional[float] = None
    average_humidity_percent: Optional[float] = None
    average_wind_speed_kmh: Optional[float] = None
    market_price_change: Optional[float] = None
    market_price_change_percentage: Optional[float] = None
    market_average_price: Optional[float] = None
    market_lowest_price: Optional[float] = None
    market_highest_price: Optional[float] = None

    model_config = ConfigDict(extra="forbid")


class PredictedDataBreakdown(BaseModel):
    """Baseline machine learning forecasts."""
    predicted_next_modal_price: Optional[float] = None
    currency: str = "Rs/Quintal"
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    price_difference_from_current: Optional[float] = None
    price_difference_percentage: Optional[float] = None
    direction: Optional[str] = None  # higher, lower, unchanged

    model_config = ConfigDict(extra="forbid")


class AssessmentDataBreakdown(BaseModel):
    """Deterministic rule-based decision engine assessments."""
    harvest_status: str  # not_ready, approaching, maturity_observed, insufficient_data
    harvest_data_sufficiency: str  # sufficient, partial, insufficient
    market_trend_status: str  # price_rising, price_falling, price_stable, insufficient_data
    market_data_sufficiency: str  # sufficient, insufficient

    model_config = ConfigDict(extra="forbid")


class CropExplanationResponse(BaseModel):
    """
    Structured explanation response translating domain indicators and baseline predictions
    into farmer-friendly insights.
    """
    crop_id: int
    crop_name: str
    farm_name: str
    farm_location: str
    summary: str = Field(..., description="High-level farmer-friendly synthesis")
    decision_explanation: str = Field(..., description="Clear explanation of harvest readiness factors")
    weather_explanation: str = Field(..., description="Contextual explanation of farm weather conditions")
    market_explanation: str = Field(..., description="Contextual explanation of mandi trading trends")
    prediction_explanation: Optional[str] = Field(None, description="Objective forecast explanation")
    observations: ObservedDataBreakdown = Field(..., description="Factual recorded observations")
    calculated: CalculatedDataBreakdown = Field(..., description="Deterministic calculated indicators")
    predicted: Optional[PredictedDataBreakdown] = Field(None, description="Model price forecast if available")
    assessment: AssessmentDataBreakdown = Field(..., description="Rule-based engine assessment results")
    limitations: List[str] = Field(..., description="Transparent system caveats and boundaries")
    provider: str = Field("rule-based-deterministic", description="Explanation provider identifier")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Generation timestamp")

    model_config = ConfigDict(extra="forbid")
