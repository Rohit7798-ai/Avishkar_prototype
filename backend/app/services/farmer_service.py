"""
Business service orchestrating domain rules and persistence for Farmer entities.
"""

from typing import List
from sqlalchemy.orm import Session

from app.core.exceptions import EntityNotFoundException
from app.models.farmer import Farmer
from app.repositories.farmer_repository import FarmerRepository
from app.schemas.farmer import FarmerCreate


class FarmerService:
    """Manages lifecycle and business validation for Farmer domain entities."""

    def __init__(self, db: Session):
        self.repository = FarmerRepository(db)

    def create_farmer(self, payload: FarmerCreate) -> Farmer:
        farmer = Farmer(
            name=payload.name.strip(),
            phone=payload.phone.strip() if payload.phone else None,
        )
        return self.repository.create(farmer)

    def get_farmer_by_id(self, farmer_id: int) -> Farmer:
        farmer = self.repository.get_by_id(farmer_id)
        if not farmer:
            raise EntityNotFoundException("Farmer", farmer_id)
        return farmer

    def list_farmers(self, skip: int = 0, limit: int = 100) -> List[Farmer]:
        return self.repository.get_all(skip=skip, limit=limit)

    def delete_farmer(self, farmer_id: int) -> None:
        farmer = self.get_farmer_by_id(farmer_id)
        self.repository.delete(farmer)
