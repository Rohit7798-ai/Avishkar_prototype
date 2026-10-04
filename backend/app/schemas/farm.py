"""
Pydantic schemas for Farm entity.
"""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class AreaUnit(str, Enum):
    """Supported area units."""
    ACRE = "acre"
    HECTARE = "hectare"


class FarmBase(BaseModel):
    """Base fields for Farm data contracts."""
    name: str = Field(..., min_length=1, max_length=120, description="Farm or parcel identifier name")
    location: str = Field(..., min_length=1, max_length=150, description="Geographic locality (e.g., Nashik, Niphad)")
    area: float = Field(..., gt=0, description="Numeric land area measurement")
    area_unit: AreaUnit = Field(default=AreaUnit.ACRE, description="Unit of measurement (acre or hectare)")


class FarmCreate(FarmBase):
    """Payload schema for creating a new Farm."""
    farmer_id: int = Field(..., gt=0, description="Foreign key reference to parent Farmer")


class FarmResponse(FarmBase):
    """Response schema representing a persisted Farm."""
    id: int
    farmer_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
