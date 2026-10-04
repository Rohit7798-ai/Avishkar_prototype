"""
Pydantic schemas for Transparent Agricultural Decision Engine assessments.
Structured, rule-based, and traceable to empirical indicators.
Zero predictions, zero scores, zero recommendations.
"""

from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict


class DecisionFactor(BaseModel):
    """An individual explanatory factor derived from observed indicators."""
    model_config = ConfigDict(from_attributes=True)

    name: str
    value: Any
    observation: str


class HarvestAssessmentResponse(BaseModel):
    """
    Transparent harvest readiness assessment based on observed crop growth stage,
    health status, observation recency, and ambient farm weather.
    """
    model_config = ConfigDict(from_attributes=True)

    crop_id: int
    status: str  # not_ready, approaching, maturity_observed, insufficient_data
    data_sufficiency: str  # sufficient, partial, insufficient
    factors: List[DecisionFactor]


class MarketAssessmentResponse(BaseModel):
    """
    Transparent market trend assessment based on empirical mandi price momentum.
    """
    model_config = ConfigDict(from_attributes=True)

    crop_name: Optional[str] = None
    market_name: Optional[str] = None
    status: str  # price_rising, price_falling, price_stable, insufficient_data
    data_sufficiency: str  # sufficient, insufficient
    factors: List[DecisionFactor]
