"""
Repository handling database persistence operations for the ObservationReminder entity.
"""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.observation_reminder import ObservationReminder


class ObservationReminderRepository:
    """Encapsulates raw data access for ObservationReminder model."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, reminder: ObservationReminder) -> ObservationReminder:
        self.db.add(reminder)
        self.db.commit()
        self.db.refresh(reminder)
        return reminder

    def get_by_crop_id(self, crop_id: int) -> Optional[ObservationReminder]:
        stmt = select(ObservationReminder).where(ObservationReminder.crop_id == crop_id)
        return self.db.scalars(stmt).first()

    def get_by_id(self, reminder_id: int) -> Optional[ObservationReminder]:
        stmt = select(ObservationReminder).where(ObservationReminder.id == reminder_id)
        return self.db.scalars(stmt).first()

    def update(self, reminder: ObservationReminder) -> ObservationReminder:
        self.db.commit()
        self.db.refresh(reminder)
        return reminder

    def delete(self, reminder: ObservationReminder) -> None:
        self.db.delete(reminder)
        self.db.commit()
