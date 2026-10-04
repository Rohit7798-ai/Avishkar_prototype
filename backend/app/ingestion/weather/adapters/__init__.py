"""
Weather provider adapters package.
"""

from app.ingestion.weather.adapters.sample_weather_adapter import SampleWeatherAdapter
from app.ingestion.weather.adapters.open_meteo_adapter import OpenMeteoAdapter

__all__ = [
    "SampleWeatherAdapter",
    "OpenMeteoAdapter",
]
