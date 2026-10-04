"""
Crop Indicator Calculation Service.
Derives deterministic crop indicators exclusively from recorded field observations.
Does NOT compute harvest recommendations or subjective scores.
"""

from datetime import date
from sqlalchemy.orm import Session

from app.core.exceptions import EntityNotFoundException
from app.repositories.crop_repository import CropRepository
from app.repositories.crop_observation_repository import CropObservationRepository
from app.schemas.indicators import CropIndicatorsResponse


class CropIndicatorService:
    """Calculates deterministic agricultural crop indicators."""

    def __init__(self, db: Session):
        self.crop_repo = CropRepository(db)
        self.obs_repo = CropObservationRepository(db)

    def get_crop_indicators(self, crop_id: int) -> CropIndicatorsResponse:
        """
        Calculates crop indicators based on empirical field observations.
        Raises EntityNotFoundException if the crop planting does not exist.
        """
        crop = self.crop_repo.get_by_id(crop_id)
        if not crop:
            raise EntityNotFoundException("Crop", crop_id)

        # ponytail: Fetch all recorded observations for this crop without pagination truncation
        observations = self.obs_repo.get_by_crop_id(crop_id, limit=None)
        count = len(observations)

        if count == 0:
            return CropIndicatorsResponse(
                crop_id=crop_id,
                latest_growth_stage=None,
                latest_health_status=None,
                latest_observation_date=None,
                observation_count=0,
                number_of_observations=0,
                days_since_latest_observation=None,
            )

        # Observations from repository are ordered by observation_date desc, id desc
        latest = observations[0]
        today = date.today()
        days_since = (today - latest.observation_date).days

        return CropIndicatorsResponse(
            crop_id=crop_id,
            latest_growth_stage=latest.growth_stage,
            latest_health_status=latest.health_status,
            latest_observation_date=latest.observation_date,
            observation_count=count,
            number_of_observations=count,
            days_since_latest_observation=days_since,
        )
