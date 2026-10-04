"""
Business service orchestrating domain rules and persistence for Crop entities.
"""

from typing import List
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleViolationException, EntityNotFoundException
from app.models.crop import Crop
from app.repositories.crop_repository import CropRepository
from app.repositories.farm_repository import FarmRepository
from app.schemas.crop import CropCreate


class CropService:
    """Manages lifecycle and business validation for Crop domain entities."""

    def __init__(self, db: Session):
        self.repository = CropRepository(db)
        self.farm_repository = FarmRepository(db)

    def create_crop(self, payload: CropCreate) -> Crop:
        # Business rule 1: A crop cannot be created for a farm that does not exist
        farm = self.farm_repository.get_by_id(payload.farm_id)
        if not farm:
            raise EntityNotFoundException("Farm", payload.farm_id)

        # Business rule 2: Area must be positive
        if payload.area <= 0:
            raise BusinessRuleViolationException("Crop area must be greater than zero")

        # Business rule 3: Dates must be logically valid
        if payload.expected_harvest_date and payload.expected_harvest_date < payload.sowing_date:
            raise BusinessRuleViolationException("Expected harvest date cannot be earlier than sowing date")

        crop = Crop(
            farm_id=payload.farm_id,
            crop_name=payload.crop_name.strip(),
            variety=payload.variety.strip() if payload.variety else None,
            sowing_date=payload.sowing_date,
            expected_harvest_date=payload.expected_harvest_date,
            area=float(payload.area),
            area_unit=payload.area_unit.value if hasattr(payload.area_unit, "value") else str(payload.area_unit),
        )
        return self.repository.create(crop)

    def get_crop_by_id(self, crop_id: int) -> Crop:
        crop = self.repository.get_by_id(crop_id)
        if not crop:
            raise EntityNotFoundException("Crop", crop_id)
        return crop

    def list_crops(self, skip: int = 0, limit: int = 100) -> List[Crop]:
        return self.repository.get_all(skip=skip, limit=limit)

    def list_crops_by_farm(self, farm_id: int) -> List[Crop]:
        # Verify farm exists to produce controlled not-found error if missing
        farm = self.farm_repository.get_by_id(farm_id)
        if not farm:
            raise EntityNotFoundException("Farm", farm_id)
        return self.repository.get_by_farm(farm_id)

    def delete_crop(self, crop_id: int) -> None:
        crop = self.get_crop_by_id(crop_id)
        self.repository.delete(crop)
