"""
Pydantic schemas for WeatherObservation entity.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class WeatherObservationBase(BaseModel):
    """Base fields for WeatherObservation data contracts with physical bounds."""
    observed_at: datetime = Field(..., description="Timestamp of weather measurement")
    temperature: float = Field(
        ...,
        ge=-50.0,
        le=60.0,
        description="Ambient air temperature in Celsius (°C)"
    )
    humidity: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Relative humidity percentage (0-100%)"
    )
    rainfall: float = Field(
        ...,
        ge=0.0,
        description="Precipitation measurement in millimeters (mm, >= 0)"
    )
    wind_speed: float = Field(
        ...,
        ge=0.0,
        description="Wind speed in kilometers per hour (km/h, >= 0)"
    )


class WeatherObservationCreate(WeatherObservationBase):
    """Payload schema for logging a new Weather observation."""
    pass


class WeatherObservationResponse(WeatherObservationBase):
    """Response schema representing a persisted Weather observation."""
    id: int
    farm_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
