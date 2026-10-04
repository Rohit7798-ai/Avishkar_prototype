"""
Repository handling database persistence operations for the Farm entity.
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.farm import Farm


class FarmRepository:
    """Encapsulates raw data access for Farm models."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, farm: Farm) -> Farm:
        self.db.add(farm)
        self.db.commit()
        self.db.refresh(farm)
        return farm

    def get_by_id(self, farm_id: int) -> Optional[Farm]:
        stmt = select(Farm).where(Farm.id == farm_id)
        return self.db.scalars(stmt).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Farm]:
        stmt = select(Farm).offset(skip).limit(limit).order_by(Farm.id.asc())
        return list(self.db.scalars(stmt).all())

    def get_by_farmer(self, farmer_id: int) -> List[Farm]:
        stmt = select(Farm).where(Farm.farmer_id == farmer_id).order_by(Farm.id.asc())
        return list(self.db.scalars(stmt).all())

    def delete(self, farm: Farm) -> None:
        self.db.delete(farm)
        self.db.commit()
