"""
API endpoints for managing crop observation reminders.
"""

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.observation_reminder import (
    ObservationReminderCreate,
    ObservationReminderResponse,
    ObservationReminderUpdate,
)
from app.services.observation_reminder_service import ObservationReminderService

router = APIRouter(prefix="/crops/{crop_id}/observation-reminder", tags=["Observation Reminders"])


@router.post(
    "",
    response_model=ObservationReminderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or initialize weekly observation reminder for a crop",
)
def create_observation_reminder(
    payload: ObservationReminderCreate,
    crop_id: int = Path(..., description="Crop parcel ID", ge=1),
    db: Session = Depends(get_db),
) -> ObservationReminderResponse:
    service = ObservationReminderService(db)
    return service.create_reminder(crop_id=crop_id, payload=payload)


@router.get(
    "",
    response_model=ObservationReminderResponse,
    status_code=status.HTTP_200_OK,
    summary="Get weekly observation reminder for a crop",
)
def get_observation_reminder(
    crop_id: int = Path(..., description="Crop parcel ID", ge=1),
    db: Session = Depends(get_db),
) -> ObservationReminderResponse:
    service = ObservationReminderService(db)
    return service.get_reminder(crop_id=crop_id)


@router.put(
    "",
    response_model=ObservationReminderResponse,
    status_code=status.HTTP_200_OK,
    summary="Update weekly observation reminder for a crop",
)
def update_observation_reminder(
    payload: ObservationReminderUpdate,
    crop_id: int = Path(..., description="Crop parcel ID", ge=1),
    db: Session = Depends(get_db),
) -> ObservationReminderResponse:
    service = ObservationReminderService(db)
    return service.update_reminder(crop_id=crop_id, payload=payload)


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete weekly observation reminder for a crop",
)
def delete_observation_reminder(
    crop_id: int = Path(..., description="Crop parcel ID", ge=1),
    db: Session = Depends(get_db),
) -> None:
    service = ObservationReminderService(db)
    service.delete_reminder(crop_id=crop_id)
