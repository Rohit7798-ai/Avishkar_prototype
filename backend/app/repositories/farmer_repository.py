"""
Repository handling database persistence operations for the Farmer entity.
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.farmer import Farmer


class FarmerRepository:
    """Encapsulates raw data access for Farmer models."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, farmer: Farmer) -> Farmer:
        self.db.add(farmer)
        self.db.commit()
        self.db.refresh(farmer)
        return farmer

    def get_by_id(self, farmer_id: int) -> Optional[Farmer]:
        stmt = select(Farmer).where(Farmer.id == farmer_id)
        return self.db.scalars(stmt).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Farmer]:
        stmt = select(Farmer).offset(skip).limit(limit).order_by(Farmer.id.asc())
        return list(self.db.scalars(stmt).all())

    def delete(self, farmer: Farmer) -> None:
        self.db.delete(farmer)
        self.db.commit()
