"""
Pydantic schemas for manual external data synchronization.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class WeatherSyncRequest(BaseModel):
    """Payload for manual farm weather synchronization."""
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Optional manual latitude coordinate")
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Optional manual longitude coordinate")
    days: Optional[int] = Field(1, ge=1, le=7, description="Past/current days to synchronize (1 = 24 hours)")

    model_config = ConfigDict(extra="forbid")


class MarketSyncRequest(BaseModel):
    """Payload for manual mandi market price synchronization."""
    crop_name: Optional[str] = Field("Onion", max_length=100, description="Target crop commodity to synchronize")
    market_name: Optional[str] = Field(None, max_length=150, description="Optional target APMC market yard")
    limit: Optional[int] = Field(50, ge=1, le=100, description="Maximum records to retrieve")

    model_config = ConfigDict(extra="forbid")


class SyncResponse(BaseModel):
    """Standardized response summarizing manual synchronization outcome."""
    provider: str = Field(..., description="Unique provider moniker")
    records_received: int = Field(..., ge=0, description="Total records retrieved from provider")
    records_accepted: int = Field(..., ge=0, description="Records validated and persisted to database")
    records_rejected: int = Field(..., ge=0, description="Records rejected (duplicates or invalid)")
    message: Optional[str] = Field(None, description="Optional operational or contextual note")

    model_config = ConfigDict(extra="forbid")
