"""
Repository handling database persistence operations for CropObservation entity.
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.crop_observation import CropObservation


class CropObservationRepository:
    """Encapsulates raw data access for CropObservation records."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, observation: CropObservation) -> CropObservation:
        self.db.add(observation)
        self.db.commit()
        self.db.refresh(observation)
        return observation

    def get_by_id(self, observation_id: int) -> Optional[CropObservation]:
        stmt = select(CropObservation).where(CropObservation.id == observation_id)
        return self.db.scalars(stmt).first()

    def get_by_crop_id(self, crop_id: int, skip: int = 0, limit: Optional[int] = 100) -> List[CropObservation]:
        stmt = (
            select(CropObservation)
            .where(CropObservation.crop_id == crop_id)
            .order_by(CropObservation.observation_date.desc(), CropObservation.id.desc())
            .offset(skip)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self.db.scalars(stmt).all())

    def delete(self, observation: CropObservation) -> None:
        self.db.delete(observation)
        self.db.commit()
