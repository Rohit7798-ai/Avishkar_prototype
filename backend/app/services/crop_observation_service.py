"""
Service orchestrating domain operations and business rules for CropObservation entity.
"""

from typing import List
from sqlalchemy.orm import Session

from app.core.exceptions import EntityNotFoundException
from app.models.crop_observation import CropObservation
from app.repositories.crop_repository import CropRepository
from app.repositories.crop_observation_repository import CropObservationRepository
from app.schemas.crop_observation import CropObservationCreate


class CropObservationService:
    """Business logic for Crop observations."""

    def __init__(self, db: Session):
        self.observation_repo = CropObservationRepository(db)
        self.crop_repo = CropRepository(db)

    def create_observation(self, crop_id: int, schema: CropObservationCreate) -> CropObservation:
        # Validate that the parent Crop entity exists
        crop = self.crop_repo.get_by_id(crop_id)
        if not crop:
            raise EntityNotFoundException("Crop", crop_id)

        observation = CropObservation(
            crop_id=crop_id,
            observation_date=schema.observation_date,
            growth_stage=schema.growth_stage.value,
            health_status=schema.health_status.value,
            notes=schema.notes,
        )
        return self.observation_repo.create(observation)

    def get_observation_by_id(self, observation_id: int) -> CropObservation:
        obs = self.observation_repo.get_by_id(observation_id)
        if not obs:
            raise EntityNotFoundException("CropObservation", observation_id)
        return obs

    def get_observations_by_crop(self, crop_id: int) -> List[CropObservation]:
        # Validate that the parent Crop entity exists
        crop = self.crop_repo.get_by_id(crop_id)
        if not crop:
            raise EntityNotFoundException("Crop", crop_id)
        return self.observation_repo.get_by_crop_id(crop_id)

    def delete_observation(self, observation_id: int) -> None:
        obs = self.observation_repo.get_by_id(observation_id)
        if not obs:
            raise EntityNotFoundException("CropObservation", observation_id)
        self.observation_repo.delete(obs)
