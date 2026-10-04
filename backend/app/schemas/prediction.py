"""
Pydantic schemas for machine learning prediction inputs and baseline evaluation outputs.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class MarketPricePredictionRequest(BaseModel):
    """Input payload for next-period market price prediction."""
    crop_name: Optional[str] = Field("Onion (Red)", max_length=100, description="Commodity name")
    market_name: Optional[str] = Field(None, max_length=150, description="Optional APMC market yard")
    current_modal_price: float = Field(..., gt=0.0, description="Current observed modal rate (Rs/Quintal)")
    price_spread: Optional[float] = Field(0.0, ge=0.0, description="Intraday price spread (max - min)")
    arrivals_tonnes: Optional[float] = Field(0.0, ge=0.0, description="Arrival volume in tonnes")

    model_config = ConfigDict(extra="forbid")


class MarketPricePredictionResponse(BaseModel):
    """Output payload from baseline market price prediction model."""
    crop_name: str = Field(..., description="Commodity name")
    market_name: Optional[str] = Field(None, description="APMC market yard")
    predicted_next_modal_price: float = Field(..., gt=0.0, description="Predicted next-day modal price")
    currency: str = Field("Rs/Quintal", description="Commercial trade unit")
    model_name: str = Field(..., description="Identifier of the forecasting model")
    model_version: str = Field(..., description="Version of the model artifact")
    features_used: Dict[str, float] = Field(..., description="Feature input values passed to the model")
    predicted_at: datetime = Field(..., description="Inference execution timestamp")

    model_config = ConfigDict(extra="forbid")


class ModelEvaluationSummaryResponse(BaseModel):
    """Summary of baseline model evaluation and comparison against naive persistence benchmark."""
    model_name: str
    model_version: str
    training_period: Dict[str, Any]
    validation_period: Dict[str, Any]
    features_used: list[str]
    model_performance: Dict[str, float]
    naive_baseline_performance: Dict[str, float]
    mae_improvement_percent: float

    model_config = ConfigDict(extra="forbid")
