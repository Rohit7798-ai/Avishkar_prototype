"""
Business service orchestrating domain rules and persistence for Farm entities.
"""

from typing import List
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleViolationException, EntityNotFoundException
from app.models.farm import Farm
from app.repositories.farm_repository import FarmRepository
from app.repositories.farmer_repository import FarmerRepository
from app.schemas.farm import FarmCreate


class FarmService:
    """Manages lifecycle and business validation for Farm domain entities."""

    def __init__(self, db: Session):
        self.repository = FarmRepository(db)
        self.farmer_repository = FarmerRepository(db)

    def create_farm(self, payload: FarmCreate) -> Farm:
        # Business rule 1: A farm cannot be created for a farmer that does not exist
        farmer = self.farmer_repository.get_by_id(payload.farmer_id)
        if not farmer:
            raise EntityNotFoundException("Farmer", payload.farmer_id)

        # Business rule 2: Area must be positive
        if payload.area <= 0:
            raise BusinessRuleViolationException("Farm area must be greater than zero")

        farm = Farm(
            farmer_id=payload.farmer_id,
            name=payload.name.strip(),
            location=payload.location.strip(),
            area=float(payload.area),
            area_unit=payload.area_unit.value if hasattr(payload.area_unit, "value") else str(payload.area_unit),
        )
        return self.repository.create(farm)

    def get_farm_by_id(self, farm_id: int) -> Farm:
        farm = self.repository.get_by_id(farm_id)
        if not farm:
            raise EntityNotFoundException("Farm", farm_id)
        return farm

    def list_farms(self, skip: int = 0, limit: int = 100) -> List[Farm]:
        return self.repository.get_all(skip=skip, limit=limit)

    def list_farms_by_farmer(self, farmer_id: int) -> List[Farm]:
        # Verify farmer exists to produce controlled not-found error if missing
        farmer = self.farmer_repository.get_by_id(farmer_id)
        if not farmer:
            raise EntityNotFoundException("Farmer", farmer_id)
        return self.repository.get_by_farmer(farmer_id)

    def delete_farm(self, farm_id: int) -> None:
        farm = self.get_farm_by_id(farm_id)
        self.repository.delete(farm)
