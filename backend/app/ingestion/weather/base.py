"""
Abstract interface definition for Weather Providers.
Decoupled entirely from database, ORM, and transport layers.
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import List

from app.ingestion.common.types import NormalizedWeatherData


class WeatherProvider(ABC):
    """
    Contract that every external weather provider adapter must fulfill.

    Guarantees:
      - Communicates only with the external weather provider.
      - Returns strictly validated NormalizedWeatherData objects.
      - Never touches SQLAlchemy models, database sessions, or web route logic.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier or moniker for the weather data provider."""
        pass

    @abstractmethod
    def fetch_current_observation(self, location_query: str) -> NormalizedWeatherData:
        """
        Fetches the latest ambient weather measurement for a given locality or coordinate pair.

        Args:
            location_query: Human-readable location (e.g. "Nashik, Maharashtra") or coordinate string.

        Returns:
            NormalizedWeatherData: Clean, validated observation.

        Raises:
            ValueError: If location cannot be resolved.
            RuntimeError: If external communication fails.
        """
        pass

    @abstractmethod
    def fetch_historical_observations(
        self,
        location_query: str,
        start_date: date,
        end_date: date,
    ) -> List[NormalizedWeatherData]:
        """
        Fetches recorded weather measurements over a historical date range.

        Args:
            location_query: Locality or coordinate string.
            start_date: Range start (inclusive).
            end_date: Range end (inclusive).

        Returns:
            List[NormalizedWeatherData]: Chronologically ordered observations.
        """
        pass
