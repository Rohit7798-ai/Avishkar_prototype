"""
Service orchestrating domain operations and business rules for MarketObservation entity.
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from app.core.exceptions import EntityNotFoundException, BusinessRuleViolationException
from app.models.market_observation import MarketObservation
from app.repositories.market_observation_repository import MarketObservationRepository
from app.schemas.market_observation import MarketObservationCreate


class MarketObservationService:
    """Business logic for Market observations."""

    def __init__(self, db: Session):
        self.observation_repo = MarketObservationRepository(db)

    def create_observation(self, schema: MarketObservationCreate) -> MarketObservation:
        # Business rule constraints
        if schema.price <= 0:
            raise BusinessRuleViolationException("Observed price must be strictly positive.")

        observation = MarketObservation(
            crop_name=schema.crop_name.strip(),
            market_name=schema.market_name.strip(),
            observed_date=schema.observed_date,
            price=schema.price,
            unit=schema.unit.strip(),
        )
        return self.observation_repo.create(observation)

    def get_observation_by_id(self, observation_id: int) -> MarketObservation:
        obs = self.observation_repo.get_by_id(observation_id)
        if not obs:
            raise EntityNotFoundException("MarketObservation", observation_id)
        return obs

    def get_observations(
        self,
        crop_name: Optional[str] = None,
        market_name: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[MarketObservation]:
        return self.observation_repo.get_all(
            crop_name=crop_name,
            market_name=market_name,
            skip=skip,
            limit=limit,
        )

    def delete_observation(self, observation_id: int) -> None:
        obs = self.observation_repo.get_by_id(observation_id)
        if not obs:
            raise EntityNotFoundException("MarketObservation", observation_id)
        self.observation_repo.delete(obs)
