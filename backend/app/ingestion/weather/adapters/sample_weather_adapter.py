"""
Sample reference weather provider adapter demonstrating external payload transformation.
Contains zero database logic, zero SQLAlchemy imports, and zero FastAPI logic.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from app.ingestion.common.types import NormalizedWeatherData
from app.ingestion.weather.base import WeatherProvider


class SampleWeatherAdapter(WeatherProvider):
    """
    Reference adapter illustrating how raw external provider payloads
    (e.g., from an Open-Meteo or IMD REST response) are parsed, mapped,
    and transformed into NormalizedWeatherData.
    """

    def __init__(self, provider_name: str = "sample_weather_source"):
        self._provider_name = provider_name

    @property
    def provider_name(self) -> str:
        return self._provider_name

    def transform_raw_payload(self, raw_data: Dict[str, Any]) -> NormalizedWeatherData:
        """
        Pure adapter transformation logic: converts foreign dictionary keys into NormalizedWeatherData.

        Example raw format:
          {
             "timestamp": "2026-10-02T12:00:00Z",
             "temp_celsius": 28.4,
             "relative_humidity": 62.0,
             "precipitation_mm": 0.0,
             "wind_speed_km_per_hr": 14.2
          }
        """
        observed_at = raw_data.get("timestamp") or raw_data.get("observed_at")
        if isinstance(observed_at, str):
            # Parse ISO timestamp
            observed_at = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))

        return NormalizedWeatherData(
            observed_at=observed_at,
            temperature_c=float(raw_data.get("temp_celsius", raw_data.get("temperature", 0.0))),
            humidity_percent=float(raw_data.get("relative_humidity", raw_data.get("humidity", 0.0))),
            rainfall_mm=float(raw_data.get("precipitation_mm", raw_data.get("rainfall", 0.0))),
            wind_speed_kmh=float(raw_data.get("wind_speed_km_per_hr", raw_data.get("wind_speed", 0.0))),
        )

    def fetch_current_observation(self, location_query: str) -> NormalizedWeatherData:
        # In a real provider, this makes an HTTP GET request to the external API.
        # For Milestone 7 (no external calls permitted), this demonstrates contract compliance.
        synthetic_raw = {
            "timestamp": datetime.now(),
            "temp_celsius": 26.5,
            "relative_humidity": 55.0,
            "precipitation_mm": 0.0,
            "wind_speed_km_per_hr": 12.0,
        }
        return self.transform_raw_payload(synthetic_raw)

    def fetch_historical_observations(
        self,
        location_query: str,
        start_date: date,
        end_date: date,
    ) -> List[NormalizedWeatherData]:
        return [self.fetch_current_observation(location_query)]
