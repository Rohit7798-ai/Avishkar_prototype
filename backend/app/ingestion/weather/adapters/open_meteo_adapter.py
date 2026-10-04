"""
Open-Meteo Weather API Provider Adapter.
Fetches real atmospheric weather data from Open-Meteo REST service
and translates responses into provider-independent NormalizedWeatherData instances.
Decoupled entirely from database models, ORM, and web transport layers.
"""

from datetime import date, datetime
import json
from typing import List, Optional, Tuple
import urllib.error
import urllib.parse
import urllib.request

from app.core.config import settings
from app.ingestion.common.types import NormalizedWeatherData
from app.ingestion.weather.base import WeatherProvider


class OpenMeteoAdapter(WeatherProvider):
    """
    Adapter implementing WeatherProvider contract for Open-Meteo API.
    Does not require an API key for non-commercial open data queries.
    """

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[float] = None):
        self.base_url = (base_url or settings.OPEN_METEO_BASE_URL).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.OPEN_METEO_TIMEOUT_SECONDS

    @property
    def provider_name(self) -> str:
        return "open-meteo"

    @staticmethod
    def parse_coordinates(location_query: str) -> Tuple[float, float]:
        """
        Parses and validates explicit coordinates from a query string.
        Format expected: "lat, lon" or "lat,lon" (e.g. "19.9975, 73.7898").
        Does NOT perform geocoding.

        Raises:
            ValueError: If string cannot be converted to valid numeric coordinates.
        """
        if not location_query or not isinstance(location_query, str):
            raise ValueError("Location query must be a non-empty string.")

        parts = [p.strip() for p in location_query.split(",")]
        if len(parts) != 2:
            raise ValueError(
                f"Coordinates required as 'latitude, longitude' (e.g. '19.9975, 73.7898'). "
                f"Received '{location_query}'. Automatic geocoding is disabled."
            )

        try:
            lat = float(parts[0])
            lon = float(parts[1])
        except ValueError:
            raise ValueError(
                f"Invalid coordinate numbers in '{location_query}'. "
                f"Latitude and longitude must be valid floating point values."
            )

        if not (-90.0 <= lat <= 90.0):
            raise ValueError(f"Latitude {lat} out of valid bounds [-90.0, 90.0].")
        if not (-180.0 <= lon <= 180.0):
            raise ValueError(f"Longitude {lon} out of valid bounds [-180.0, 180.0].")

        return lat, lon

    def _execute_request(self, endpoint: str, params: dict) -> dict:
        """Helper to execute an HTTP GET request using standard library urllib."""
        query_string = urllib.parse.urlencode(params)
        url = f"{self.base_url}/{endpoint}?{query_string}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "FarmerDecisionSupport/1.0",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                payload = response.read().decode("utf-8")
                return json.loads(payload)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Open-Meteo HTTP error {exc.code}: {exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Open-Meteo connection error: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"Open-Meteo returned invalid JSON: {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"Open-Meteo request failure: {exc}") from exc

    def fetch_current_observation(self, location_query: str) -> NormalizedWeatherData:
        """
        Fetches current weather measurement for given coordinates.

        Args:
            location_query: Coordinate string in "latitude, longitude" format.
        """
        lat, lon = self.parse_coordinates(location_query)
        data = self._execute_request(
            "forecast",
            {
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
            },
        )

        current = data.get("current")
        if not current or not isinstance(current, dict):
            raise ValueError("Malformed Open-Meteo response: 'current' object missing.")

        time_str = current.get("time")
        temp = current.get("temperature_2m")
        hum = current.get("relative_humidity_2m")
        rain = current.get("precipitation")
        wind = current.get("wind_speed_10m")

        if time_str is None or temp is None or hum is None or rain is None or wind is None:
            raise ValueError(
                "Malformed Open-Meteo response: missing required current measurement fields."
            )

        try:
            observed_at = datetime.fromisoformat(time_str)
        except ValueError as exc:
            raise ValueError(f"Malformed observation timestamp '{time_str}': {exc}") from exc

        return NormalizedWeatherData(
            observed_at=observed_at,
            temperature_c=float(temp),
            humidity_percent=float(hum),
            rainfall_mm=float(rain),
            wind_speed_kmh=float(wind),
        )

    def fetch_historical_observations(
        self,
        location_query: str,
        start_date: date,
        end_date: date,
    ) -> List[NormalizedWeatherData]:
        """
        Fetches recorded hourly weather measurements for a date range.
        """
        lat, lon = self.parse_coordinates(location_query)
        if start_date > end_date:
            raise ValueError("start_date cannot be after end_date.")

        data = self._execute_request(
            "forecast",
            {
                "latitude": lat,
                "longitude": lon,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
            },
        )

        return self._normalize_hourly_payload(data)

    def fetch_recent_observations(
        self,
        location_query: str,
        past_days: int = 1,
    ) -> List[NormalizedWeatherData]:
        """
        Fetches recent hourly weather measurements up to the current day.
        Default past_days=1 gives 24 hours of measurements.
        """
        lat, lon = self.parse_coordinates(location_query)
        days = max(1, min(past_days, 7))
        data = self._execute_request(
            "forecast",
            {
                "latitude": lat,
                "longitude": lon,
                "past_days": days,
                "forecast_days": 1,
                "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
            },
        )

        return self._normalize_hourly_payload(data)

    def _normalize_hourly_payload(self, data: dict) -> List[NormalizedWeatherData]:
        """Parses an Open-Meteo hourly response block into NormalizedWeatherData list."""
        hourly = data.get("hourly")
        if not hourly or not isinstance(hourly, dict):
            raise ValueError("Malformed Open-Meteo response: 'hourly' object missing.")

        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        hums = hourly.get("relative_humidity_2m", [])
        rains = hourly.get("precipitation", [])
        winds = hourly.get("wind_speed_10m", [])

        if not (len(times) == len(temps) == len(hums) == len(rains) == len(winds)):
            raise ValueError("Malformed Open-Meteo response: mismatched hourly array lengths.")

        normalized_records: List[NormalizedWeatherData] = []
        for t_str, temp, hum, rain, wind in zip(times, temps, hums, rains, winds):
            # Skip entries with null measurements if provider returned partial future forecast
            if temp is None or hum is None or rain is None or wind is None:
                continue
            try:
                dt = datetime.fromisoformat(t_str)
                record = NormalizedWeatherData(
                    observed_at=dt,
                    temperature_c=float(temp),
                    humidity_percent=float(hum),
                    rainfall_mm=float(rain),
                    wind_speed_kmh=float(wind),
                )
                normalized_records.append(record)
            except (ValueError, TypeError):
                continue

        return normalized_records
