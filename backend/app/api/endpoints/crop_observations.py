"""
REST API endpoints for CropObservation entity.
Mounted under /api/v1.
"""

from typing import List
from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.crop_observation import CropObservationCreate, CropObservationResponse
from app.services.crop_observation_service import CropObservationService

router = APIRouter(tags=["Crop Observations"])


@router.post(
    "/crops/{crop_id}/observations",
    response_model=CropObservationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record Crop Observation",
    description="Records a new empirical field observation for a specific crop planting.",
)
def record_crop_observation(
    crop_id: int,
    payload: CropObservationCreate,
    db: Session = Depends(get_db),
) -> CropObservationResponse:
    service = CropObservationService(db)
    obs = service.create_observation(crop_id, payload)
    return CropObservationResponse.model_validate(obs)


@router.get(
    "/crops/{crop_id}/observations",
    response_model=List[CropObservationResponse],
    status_code=status.HTTP_200_OK,
    summary="List Crop Observations",
    description="Retrieves all recorded observations for a given crop planting.",
)
def list_crop_observations(
    crop_id: int,
    db: Session = Depends(get_db),
) -> List[CropObservationResponse]:
    service = CropObservationService(db)
    observations = service.get_observations_by_crop(crop_id)
    return [CropObservationResponse.model_validate(item) for item in observations]


@router.delete(
    "/crop-observations/{observation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Crop Observation",
    description="Deletes a specific crop observation record.",
)
def delete_crop_observation(
    observation_id: int,
    db: Session = Depends(get_db),
) -> Response:
    service = CropObservationService(db)
    service.delete_observation(observation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
