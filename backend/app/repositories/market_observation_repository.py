"""
Repository handling database persistence operations for MarketObservation entity.
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.market_observation import MarketObservation


class MarketObservationRepository:
    """Encapsulates raw data access for MarketObservation records."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, observation: MarketObservation) -> MarketObservation:
        self.db.add(observation)
        self.db.commit()
        self.db.refresh(observation)
        return observation

    def get_by_id(self, observation_id: int) -> Optional[MarketObservation]:
        stmt = select(MarketObservation).where(MarketObservation.id == observation_id)
        return self.db.scalars(stmt).first()

    def get_all(
        self,
        crop_name: Optional[str] = None,
        market_name: Optional[str] = None,
        skip: int = 0,
        limit: Optional[int] = 100,
    ) -> List[MarketObservation]:
        stmt = select(MarketObservation)
        if crop_name:
            stmt = stmt.where(MarketObservation.crop_name == crop_name)
        if market_name:
            stmt = stmt.where(MarketObservation.market_name == market_name)
        stmt = stmt.order_by(MarketObservation.observed_date.desc(), MarketObservation.id.desc()).offset(skip)
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self.db.scalars(stmt).all())

    def find_by_crop_market_date(self, crop_name: str, market_name: str, observed_date) -> Optional[MarketObservation]:
        stmt = select(MarketObservation).where(
            MarketObservation.crop_name == crop_name,
            MarketObservation.market_name == market_name,
            MarketObservation.observed_date == observed_date,
        )
        return self.db.scalars(stmt).first()

    def delete(self, observation: MarketObservation) -> None:
        self.db.delete(observation)
        self.db.commit()
