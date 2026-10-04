"""
Crop ORM domain model.
"""

from datetime import date
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.farm import Farm
    from app.models.crop_observation import CropObservation
    from app.models.observation_reminder import ObservationReminder


class Crop(Base, TimestampMixin):
    """
    Crop entity representing a specific agricultural planting on a Farm.

    Cascading Behavior:
        - Belongs to a Farm (`farm_id` foreign key with `ondelete="CASCADE"`).
        - Deletion of the parent Farm cascades to remove the associated Crop records.
        - Deletion of the Crop cascades to remove associated CropObservation records.
        - Deletion of the Crop cascades to remove associated ObservationReminder record.
    """
    __tablename__ = "crops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    farm_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("farms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    crop_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    variety: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sowing_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_harvest_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    area: Mapped[float] = mapped_column(Float, nullable=False)
    area_unit: Mapped[str] = mapped_column(String(20), nullable=False, default="acre")

    # Relationships
    farm: Mapped["Farm"] = relationship("Farm", back_populates="crops")
    observations: Mapped[List["CropObservation"]] = relationship(
        "CropObservation",
        back_populates="crop",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    observation_reminder: Mapped[Optional["ObservationReminder"]] = relationship(
        "ObservationReminder",
        back_populates="crop",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return (
            f"<Crop(id={self.id}, name='{self.crop_name}', variety='{self.variety}', "
            f"sowing_date={self.sowing_date}, area={self.area} {self.area_unit})>"
        )
