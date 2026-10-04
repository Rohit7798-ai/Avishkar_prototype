"""
Pydantic schemas for CropObservation entity.
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class GrowthStage(str, Enum):
    """Permitted crop growth lifecycle stages."""
    EARLY = "early"
    VEGETATIVE = "vegetative"
    FLOWERING = "flowering"
    FRUITING = "fruiting"
    MATURITY = "maturity"
    POST_MATURITY = "post_maturity"


class HealthStatus(str, Enum):
    """Permitted plant health and vigor status values."""
    HEALTHY = "healthy"
    MODERATE = "moderate"
    STRESSED = "stressed"
    DAMAGED = "damaged"


class CropObservationBase(BaseModel):
    """Base fields for CropObservation data contracts."""
    observation_date: date = Field(..., description="Date of field observation")
    growth_stage: GrowthStage = Field(..., description="Observed growth stage")
    health_status: HealthStatus = Field(..., description="Observed crop health status")
    notes: Optional[str] = Field(None, max_length=1000, description="Field scout or farmer notes")


class CropObservationCreate(CropObservationBase):
    """Payload schema for logging a new Crop observation."""
    pass


class CropObservationResponse(CropObservationBase):
    """Response schema representing a persisted Crop observation."""
    id: int
    crop_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
