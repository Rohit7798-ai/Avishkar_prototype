"""
Pydantic schemas for ObservationReminder entity.
"""

from datetime import datetime
from enum import Enum
import re
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Weekday(str, Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


TIME_REGEX = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


class ObservationReminderBase(BaseModel):
    enabled: bool = Field(default=True, description="Whether recurring reminder is enabled")
    weekday: Weekday = Field(default=Weekday.SUNDAY, description="Day of week for reminder (monday - sunday)")
    reminder_time: str = Field(default="08:00", description="Time of day for reminder in HH:MM format (24-hour)")

    @field_validator("weekday", mode="before")
    @classmethod
    def normalize_weekday(cls, v):
        if isinstance(v, str):
            v_clean = v.strip().lower()
            try:
                return Weekday(v_clean)
            except ValueError:
                raise ValueError(f"Invalid weekday '{v}'. Must be one of {[w.value for w in Weekday]}")
        return v

    @field_validator("reminder_time")
    @classmethod
    def validate_reminder_time(cls, v: str) -> str:
        v_clean = v.strip()
        if not TIME_REGEX.match(v_clean):
            raise ValueError(f"Invalid reminder time '{v}'. Expected 24-hour HH:MM format (e.g. '08:00', '17:30').")
        return v_clean


class ObservationReminderCreate(ObservationReminderBase):
    pass


class ObservationReminderUpdate(BaseModel):
    enabled: Optional[bool] = Field(None, description="Whether recurring reminder is enabled")
    weekday: Optional[Weekday] = Field(None, description="Day of week for reminder (monday - sunday)")
    reminder_time: Optional[str] = Field(None, description="Time of day for reminder in HH:MM format (24-hour)")

    @field_validator("weekday", mode="before")
    @classmethod
    def normalize_weekday(cls, v):
        if v is not None and isinstance(v, str):
            v_clean = v.strip().lower()
            try:
                return Weekday(v_clean)
            except ValueError:
                raise ValueError(f"Invalid weekday '{v}'. Must be one of {[w.value for w in Weekday]}")
        return v

    @field_validator("reminder_time")
    @classmethod
    def validate_reminder_time(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v_clean = v.strip()
        if not TIME_REGEX.match(v_clean):
            raise ValueError(f"Invalid reminder time '{v}'. Expected 24-hour HH:MM format (e.g. '08:00', '17:30').")
        return v_clean


class ObservationReminderResponse(ObservationReminderBase):
    id: int
    crop_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
