"""
Service orchestrating domain rules and persistence for Crop Observation Reminders.
"""

from typing import Optional
from sqlalchemy.orm import Session

from app.core.exceptions import EntityNotFoundException
from app.models.observation_reminder import ObservationReminder
from app.repositories.crop_repository import CropRepository
from app.repositories.observation_reminder_repository import ObservationReminderRepository
from app.schemas.observation_reminder import (
    ObservationReminderCreate,
    ObservationReminderUpdate,
)


class ObservationReminderService:
    """Manages lifecycle and business validation for ObservationReminder domain entities."""

    def __init__(self, db: Session):
        self.repository = ObservationReminderRepository(db)
        self.crop_repository = CropRepository(db)

    def get_reminder(self, crop_id: int) -> ObservationReminder:
        """Retrieves active or configured reminder for a crop."""
        crop = self.crop_repository.get_by_id(crop_id)
        if not crop:
            raise EntityNotFoundException("Crop", crop_id)

        reminder = self.repository.get_by_crop_id(crop_id)
        if not reminder:
            raise EntityNotFoundException("ObservationReminder", crop_id)
        return reminder

    def create_reminder(self, crop_id: int, payload: ObservationReminderCreate) -> ObservationReminder:
        """Creates or upserts weekly observation reminder for a crop."""
        crop = self.crop_repository.get_by_id(crop_id)
        if not crop:
            raise EntityNotFoundException("Crop", crop_id)

        weekday_str = payload.weekday.value if hasattr(payload.weekday, "value") else str(payload.weekday).lower()
        existing = self.repository.get_by_crop_id(crop_id)
        if existing:
            existing.enabled = payload.enabled
            existing.weekday = weekday_str
            existing.reminder_time = payload.reminder_time
            return self.repository.update(existing)

        reminder = ObservationReminder(
            crop_id=crop_id,
            enabled=payload.enabled,
            weekday=weekday_str,
            reminder_time=payload.reminder_time,
        )
        return self.repository.create(reminder)

    def update_reminder(self, crop_id: int, payload: ObservationReminderUpdate) -> ObservationReminder:
        """Updates fields on an existing weekly observation reminder."""
        crop = self.crop_repository.get_by_id(crop_id)
        if not crop:
            raise EntityNotFoundException("Crop", crop_id)

        reminder = self.repository.get_by_crop_id(crop_id)
        if not reminder:
            raise EntityNotFoundException("ObservationReminder", crop_id)

        if payload.enabled is not None:
            reminder.enabled = payload.enabled
        if payload.weekday is not None:
            reminder.weekday = payload.weekday.value if hasattr(payload.weekday, "value") else str(payload.weekday).lower()
        if payload.reminder_time is not None:
            reminder.reminder_time = payload.reminder_time

        return self.repository.update(reminder)

    def delete_reminder(self, crop_id: int) -> None:
        """Deletes weekly observation reminder for a crop."""
        crop = self.crop_repository.get_by_id(crop_id)
        if not crop:
            raise EntityNotFoundException("Crop", crop_id)

        reminder = self.repository.get_by_crop_id(crop_id)
        if not reminder:
            raise EntityNotFoundException("ObservationReminder", crop_id)

        self.repository.delete(reminder)
