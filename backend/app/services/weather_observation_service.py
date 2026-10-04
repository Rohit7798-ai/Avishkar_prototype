"""
Service orchestrating domain operations and business rules for WeatherObservation entity.
"""

from typing import List
from sqlalchemy.orm import Session

from app.core.exceptions import EntityNotFoundException, BusinessRuleViolationException
from app.models.weather_observation import WeatherObservation
from app.repositories.farm_repository import FarmRepository
from app.repositories.weather_observation_repository import WeatherObservationRepository
from app.schemas.weather_observation import WeatherObservationCreate


class WeatherObservationService:
    """Business logic for Weather observations."""

    def __init__(self, db: Session):
        self.observation_repo = WeatherObservationRepository(db)
        self.farm_repo = FarmRepository(db)

    def create_observation(self, farm_id: int, schema: WeatherObservationCreate) -> WeatherObservation:
        # Validate that parent Farm exists
        farm = self.farm_repo.get_by_id(farm_id)
        if not farm:
            raise EntityNotFoundException("Farm", farm_id)

        # Domain level physical validation constraints
        if schema.rainfall < 0:
            raise BusinessRuleViolationException("Rainfall cannot be negative.")
        if schema.humidity < 0 or schema.humidity > 100:
            raise BusinessRuleViolationException("Humidity must be between 0 and 100 percent.")
        if schema.wind_speed < 0:
            raise BusinessRuleViolationException("Wind speed cannot be negative.")

        observation = WeatherObservation(
            farm_id=farm_id,
            observed_at=schema.observed_at,
            temperature=schema.temperature,
            humidity=schema.humidity,
            rainfall=schema.rainfall,
            wind_speed=schema.wind_speed,
        )
        return self.observation_repo.create(observation)

    def get_observation_by_id(self, observation_id: int) -> WeatherObservation:
        obs = self.observation_repo.get_by_id(observation_id)
        if not obs:
            raise EntityNotFoundException("WeatherObservation", observation_id)
        return obs

    def get_observations_by_farm(self, farm_id: int) -> List[WeatherObservation]:
        # Validate that parent Farm exists
        farm = self.farm_repo.get_by_id(farm_id)
        if not farm:
            raise EntityNotFoundException("Farm", farm_id)
        return self.observation_repo.get_by_farm_id(farm_id)

    def delete_observation(self, observation_id: int) -> None:
        obs = self.observation_repo.get_by_id(observation_id)
        if not obs:
            raise EntityNotFoundException("WeatherObservation", observation_id)
        self.observation_repo.delete(obs)
