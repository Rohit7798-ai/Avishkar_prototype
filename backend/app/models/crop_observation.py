"""
Crop Observation ORM domain model.
"""

from datetime import date
from enum import Enum
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.crop import Crop


class GrowthStage(str, Enum):
    """Controlled growth stages across crop lifecycle."""
    EARLY = "early"
    VEGETATIVE = "vegetative"
    FLOWERING = "flowering"
    FRUITING = "fruiting"
    MATURITY = "maturity"
    POST_MATURITY = "post_maturity"


class HealthStatus(str, Enum):
    """Controlled plant health and vigor status."""
    HEALTHY = "healthy"
    MODERATE = "moderate"
    STRESSED = "stressed"
    DAMAGED = "damaged"


class CropObservation(Base, TimestampMixin):
    """
    Records empirical observations about crop growth and physical health.
    Represents facts recorded by users or field scouts, not AI predictions.
    """
    __tablename__ = "crop_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    crop_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("crops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    observation_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    growth_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    health_status: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    crop: Mapped["Crop"] = relationship("Crop", back_populates="observations")

    def __repr__(self) -> str:
        return (
            f"<CropObservation(id={self.id}, crop_id={self.crop_id}, "
            f"date={self.observation_date}, stage='{self.growth_stage}', health='{self.health_status}')>"
        )
