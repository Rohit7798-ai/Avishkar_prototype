"""
Repository handling database persistence operations for WeatherObservation entity.
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.weather_observation import WeatherObservation


class WeatherObservationRepository:
    """Encapsulates raw data access for WeatherObservation records."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, observation: WeatherObservation) -> WeatherObservation:
        self.db.add(observation)
        self.db.commit()
        self.db.refresh(observation)
        return observation

    def get_by_id(self, observation_id: int) -> Optional[WeatherObservation]:
        stmt = select(WeatherObservation).where(WeatherObservation.id == observation_id)
        return self.db.scalars(stmt).first()

    def get_by_farm_id(self, farm_id: int, skip: int = 0, limit: Optional[int] = 100) -> List[WeatherObservation]:
        stmt = (
            select(WeatherObservation)
            .where(WeatherObservation.farm_id == farm_id)
            .order_by(WeatherObservation.observed_at.desc(), WeatherObservation.id.desc())
            .offset(skip)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self.db.scalars(stmt).all())

    def find_by_farm_and_time(self, farm_id: int, observed_at) -> Optional[WeatherObservation]:
        stmt = select(WeatherObservation).where(
            WeatherObservation.farm_id == farm_id,
            WeatherObservation.observed_at == observed_at,
        )
        return self.db.scalars(stmt).first()

    def delete(self, observation: WeatherObservation) -> None:
        self.db.delete(observation)
        self.db.commit()
