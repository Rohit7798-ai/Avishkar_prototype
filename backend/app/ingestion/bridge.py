"""
Integration bridge connecting normalized ingestion data to existing domain observation services.
Maintains architectural boundary: Adapter -> Normalized Data -> Service -> Repository -> DB.
Does NOT bypass service/repository layers. Does NOT directly manipulate database models.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from app.ingestion.common.types import NormalizedWeatherData, NormalizedMarketData
from app.models.weather_observation import WeatherObservation
from app.models.market_observation import MarketObservation
from app.schemas.weather_observation import WeatherObservationCreate
from app.schemas.market_observation import MarketObservationCreate

if TYPE_CHECKING:
    from app.services.weather_observation_service import WeatherObservationService
    from app.services.market_observation_service import MarketObservationService


def ingest_weather_observation(
    farm_id: int,
    data: NormalizedWeatherData,
    service: WeatherObservationService,
) -> WeatherObservation:
    """
    Bridges validated normalized weather data to the existing WeatherObservationService.

    Args:
        farm_id: Foreign key ID of the target farm parcel.
        data: Validated NormalizedWeatherData instance.
        service: Injected WeatherObservationService instance.

    Returns:
        WeatherObservation: Persisted domain entity.
    """
    schema = WeatherObservationCreate(
        observed_at=data.observed_at,
        temperature=data.temperature_c,
        humidity=data.humidity_percent,
        rainfall=data.rainfall_mm,
        wind_speed=data.wind_speed_kmh,
    )
    return service.create_observation(farm_id, schema)


def ingest_market_observation(
    data: NormalizedMarketData,
    service: MarketObservationService,
) -> MarketObservation:
    """
    Bridges validated normalized market data to the existing MarketObservationService.

    Args:
        data: Validated NormalizedMarketData instance.
        service: Injected MarketObservationService instance.

    Returns:
        MarketObservation: Persisted domain entity.
    """
    schema = MarketObservationCreate(
        crop_name=data.crop_name,
        market_name=data.market_name,
        observed_date=data.observed_date,
        price=data.price,
        unit=data.unit,
    )
    return service.create_observation(schema)
