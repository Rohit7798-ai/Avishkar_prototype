"""
Repository handling database persistence operations for the Crop entity.
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.crop import Crop


class CropRepository:
    """Encapsulates raw data access for Crop models."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, crop: Crop) -> Crop:
        self.db.add(crop)
        self.db.commit()
        self.db.refresh(crop)
        return crop

    def get_by_id(self, crop_id: int) -> Optional[Crop]:
        stmt = select(Crop).where(Crop.id == crop_id)
        return self.db.scalars(stmt).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Crop]:
        stmt = select(Crop).offset(skip).limit(limit).order_by(Crop.id.asc())
        return list(self.db.scalars(stmt).all())

    def get_by_farm(self, farm_id: int) -> List[Crop]:
        stmt = select(Crop).where(Crop.farm_id == farm_id).order_by(Crop.id.asc())
        return list(self.db.scalars(stmt).all())

    def delete(self, crop: Crop) -> None:
        self.db.delete(crop)
        self.db.commit()
