"""
Provider-independent normalized data structures for agricultural observations.
Completely decoupled from database ORM (SQLAlchemy) and web transport (FastAPI).
"""

from datetime import date, datetime
from typing import Any, Dict
from pydantic import BaseModel, ConfigDict, Field, field_validator


class NormalizedWeatherData(BaseModel):
    """
    Standardized, provider-independent weather observation data contract.

    Attributes:
        observed_at: Timestamp of the physical measurement.
        temperature_c: Ambient dry-bulb temperature in Celsius (°C).
        humidity_percent: Relative humidity percentage [0.0 - 100.0].
        rainfall_mm: Total precipitation in millimeters (>= 0.0).
        wind_speed_kmh: Wind speed in kilometers per hour (>= 0.0).
    """
    observed_at: datetime = Field(..., description="Timestamp of the physical measurement")
    temperature_c: float = Field(..., ge=-50.0, le=60.0, description="Temperature in Celsius (-50°C to +60°C)")
    humidity_percent: float = Field(..., ge=0.0, le=100.0, description="Relative humidity percentage (0-100%)")
    rainfall_mm: float = Field(..., ge=0.0, description="Precipitation in millimeters (>= 0)")
    wind_speed_kmh: float = Field(..., ge=0.0, description="Wind speed in km/h (>= 0)")

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("temperature_c", "humidity_percent", "rainfall_mm", "wind_speed_kmh")
    @classmethod
    def validate_finite_numbers(cls, v: float) -> float:
        if v != v:  # NaN check
            raise ValueError("Measurement value cannot be NaN")
        return round(float(v), 2)


class NormalizedMarketData(BaseModel):
    """
    Standardized, provider-independent mandi market price data contract.

    Attributes:
        crop_name: Normalized commodity name (e.g. Onion).
        market_name: Standardized APMC market name (e.g. Lasalgaon APMC).
        observed_date: Calendar date of the recorded rate.
        price: Observed modal/traded price (> 0.0).
        unit: Commercial trade measurement unit (e.g. Rs/Quintal, Rs/kg).
    """
    crop_name: str = Field(..., min_length=1, max_length=100, description="Standardized crop name")
    market_name: str = Field(..., min_length=1, max_length=150, description="APMC market name")
    observed_date: date = Field(..., description="Date of market rate quote")
    price: float = Field(..., gt=0.0, description="Observed price (must be strictly positive)")
    unit: str = Field(..., min_length=1, max_length=50, description="Trade quantity unit")

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("crop_name", "market_name", "unit")
    @classmethod
    def validate_non_empty_strings(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Field cannot be empty or solely whitespace")
        return stripped

    @field_validator("price")
    @classmethod
    def validate_positive_price(cls, v: float) -> float:
        if v != v:  # NaN check
            raise ValueError("Price cannot be NaN")
        if v <= 0:
            raise ValueError("Price must be strictly positive")
        return round(float(v), 2)
