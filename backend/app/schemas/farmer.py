"""
Pydantic schemas for Farmer entity.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class FarmerBase(BaseModel):
    """Base fields for Farmer data contracts."""
    name: str = Field(..., min_length=1, max_length=120, description="Farmer full name")
    phone: Optional[str] = Field(None, max_length=25, description="Contact phone number")


class FarmerCreate(FarmerBase):
    """Payload schema for creating a new Farmer."""
    pass


class FarmerResponse(FarmerBase):
    """Response schema representing a persisted Farmer."""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
