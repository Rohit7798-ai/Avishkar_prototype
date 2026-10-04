"""
Observation Reminder ORM domain model.
Configures recurring weekly reminders for recording crop observations.
"""

from typing import TYPE_CHECKING
from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.crop import Crop


class ObservationReminder(Base, TimestampMixin):
    """
    Weekly observation reminder entity associated with a specific Crop.
    1-to-0..1 relationship with Crop.
    """
    __tablename__ = "observation_reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    crop_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("crops.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    weekday: Mapped[str] = mapped_column(String(20), nullable=False)  # "monday", "sunday", etc.
    reminder_time: Mapped[str] = mapped_column(String(10), nullable=False)  # "08:00" (HH:MM format)

    # Relationships
    crop: Mapped["Crop"] = relationship("Crop", back_populates="observation_reminder")

    def __repr__(self) -> str:
        return (
            f"<ObservationReminder(id={self.id}, crop_id={self.crop_id}, "
            f"enabled={self.enabled}, weekday='{self.weekday}', time='{self.reminder_time}')>"
        )
