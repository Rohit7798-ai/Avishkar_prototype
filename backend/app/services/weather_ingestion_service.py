"""
Orchestration service for external weather observation ingestion.
Connects Farm entity -> Coordinates -> WeatherProvider Adapter -> Normalized Data
-> Validation -> WeatherObservationService -> SQLite.
Preserves architectural purity: No database code inside adapters.
"""

from typing import Any, Dict, Optional, Set
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleViolationException, EntityNotFoundException
from app.ingestion.bridge import ingest_weather_observation
from app.ingestion.weather.adapters.open_meteo_adapter import OpenMeteoAdapter
from app.ingestion.weather.base import WeatherProvider
from app.repositories.farm_repository import FarmRepository
from app.repositories.weather_observation_repository import WeatherObservationRepository
from app.services.weather_observation_service import WeatherObservationService


class WeatherIngestionService:
    """Orchestrates manual synchronization of weather observations from external providers."""

    def __init__(
        self,
        db: Session,
        weather_provider: Optional[WeatherProvider] = None,
    ):
        self.db = db
        self.farm_repo = FarmRepository(db)
        self.observation_repo = WeatherObservationRepository(db)
        self.observation_service = WeatherObservationService(db)
        self.weather_provider = weather_provider or OpenMeteoAdapter()

    @staticmethod
    def _parse_coordinates_from_location(location_str: str) -> Optional[tuple[float, float]]:
        """
        Attempts to parse latitude and longitude from a coordinate string.
        Returns (lat, lon) if valid, or None if the string is a named locality.
        """
        if not location_str or not isinstance(location_str, str):
            return None
        parts = [p.strip() for p in location_str.split(",")]
        if len(parts) == 2:
            try:
                lat = float(parts[0])
                lon = float(parts[1])
                if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                    return lat, lon
            except ValueError:
                return None
        return None

    def sync_farm_weather(
        self,
        farm_id: int,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        days: int = 1,
    ) -> Dict[str, Any]:
        """
        Manually synchronizes weather observations for a target farm.

        Args:
            farm_id: Target Farm parcel ID.
            latitude: Optional manual latitude coordinate.
            longitude: Optional manual longitude coordinate.
            days: Number of past/current days to synchronize (1 = 24 hourly records).

        Returns:
            Dict containing provider, records_received, records_accepted, records_rejected.
        """
        farm = self.farm_repo.get_by_id(farm_id)
        if not farm:
            raise EntityNotFoundException("Farm", farm_id)

        # Coordinate resolution: explicit parameters take precedence over farm.location
        resolved_coords: Optional[tuple[float, float]] = None
        if latitude is not None and longitude is not None:
            if not (-90.0 <= latitude <= 90.0):
                raise BusinessRuleViolationException(f"Latitude {latitude} out of valid bounds [-90.0, 90.0].")
            if not (-180.0 <= longitude <= 180.0):
                raise BusinessRuleViolationException(f"Longitude {longitude} out of valid bounds [-180.0, 180.0].")
            resolved_coords = (latitude, longitude)
        else:
            resolved_coords = self._parse_coordinates_from_location(farm.location)

        if not resolved_coords:
            raise BusinessRuleViolationException(
                f"Coordinates (latitude and longitude) are required for external weather ingestion. "
                f"Farm location '{farm.location}' does not contain valid numeric coordinates ('lat, lon') "
                f"and none were provided. Automatic geocoding is disabled."
            )

        coord_str = f"{resolved_coords[0]}, {resolved_coords[1]}"

        # Fetch normalized records from provider
        try:
            records = self.weather_provider.fetch_recent_observations(coord_str, past_days=days)
        except Exception as exc:
            raise BusinessRuleViolationException(f"Weather provider sync failed: {exc}") from exc

        records_received = len(records)
        records_accepted = 0
        records_rejected = 0
        seen_timestamps: Set[Any] = set()

        for record in records:
            # Duplicate detection: in-batch duplicate check
            if record.observed_at in seen_timestamps:
                records_rejected += 1
                continue

            # Duplicate detection: database-level duplicate check
            existing = self.observation_repo.find_by_farm_and_time(farm_id, record.observed_at)
            if existing:
                records_rejected += 1
                continue

            try:
                # Ingest through existing observation service and validation layer
                ingest_weather_observation(
                    farm_id=farm_id,
                    data=record,
                    service=self.observation_service,
                )
                seen_timestamps.add(record.observed_at)
                records_accepted += 1
            except Exception:
                records_rejected += 1

        return {
            "provider": self.weather_provider.provider_name,
            "records_received": records_received,
            "records_accepted": records_accepted,
            "records_rejected": records_rejected,
        }
