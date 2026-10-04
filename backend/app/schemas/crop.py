"""
Pydantic schemas for Crop entity.
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.farm import AreaUnit


class CropBase(BaseModel):
    """Base fields for Crop data contracts."""
    crop_name: str = Field(..., min_length=1, max_length=100, description="Common crop name (e.g. Onion)")
    variety: Optional[str] = Field(None, max_length=100, description="Cultivar or variety (e.g. Bhima Super)")
    sowing_date: date = Field(..., description="Planting or transplanting date")
    expected_harvest_date: Optional[date] = Field(None, description="Target expected harvest date")
    area: float = Field(..., gt=0, description="Planted area measurement")
    area_unit: AreaUnit = Field(default=AreaUnit.ACRE, description="Unit of measurement (acre or hectare)")

    @model_validator(mode="after")
    def validate_harvest_date_after_sowing(self):
        if self.expected_harvest_date and self.sowing_date:
            if self.expected_harvest_date < self.sowing_date:
                raise ValueError("expected_harvest_date cannot be before sowing_date")
        return self


class CropCreate(CropBase):
    """Payload schema for creating a new Crop planting."""
    farm_id: int = Field(..., gt=0, description="Foreign key reference to parent Farm")


class CropResponse(CropBase):
    """Response schema representing a persisted Crop."""
    id: int
    farm_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
