"""
Provider-independent data ingestion architecture package.
Deconstructs external observation sources into normalized domain contracts.
"""

from app.ingestion.common.types import NormalizedWeatherData, NormalizedMarketData
from app.ingestion.weather.base import WeatherProvider
from app.ingestion.market.base import MarketProvider
from app.ingestion.bridge import ingest_weather_observation, ingest_market_observation

__all__ = [
    "NormalizedWeatherData",
    "NormalizedMarketData",
    "WeatherProvider",
    "MarketProvider",
    "ingest_weather_observation",
    "ingest_market_observation",
]
