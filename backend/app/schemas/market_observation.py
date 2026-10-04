"""
Pydantic schemas for MarketObservation entity.
"""

from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field


class MarketObservationBase(BaseModel):
    """Base fields for MarketObservation data contracts."""
    crop_name: str = Field(..., min_length=1, max_length=100, description="Observed commodity name (e.g. Onion)")
    market_name: str = Field(..., min_length=1, max_length=150, description="APMC market yard or trading center")
    observed_date: date = Field(..., description="Date of market price quote")
    price: float = Field(..., gt=0.0, description="Observed modal/traded price (must be > 0)")
    unit: str = Field(..., min_length=1, max_length=50, description="Trading quantity unit (e.g. Rs/Quintal, Rs/kg)")


class MarketObservationCreate(MarketObservationBase):
    """Payload schema for logging a new Market observation."""
    pass


class MarketObservationResponse(MarketObservationBase):
    """Response schema representing a persisted Market observation."""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
