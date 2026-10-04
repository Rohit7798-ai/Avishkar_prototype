"""
Farm ORM domain model.
"""

from typing import List, TYPE_CHECKING
from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.farmer import Farmer
    from app.models.crop import Crop
    from app.models.weather_observation import WeatherObservation


class Farm(Base, TimestampMixin):
    """
    Farm entity representing an agricultural land parcel owned by a Farmer.

    Cascading Behavior:
        - Belongs to a Farmer (`farmer_id` foreign key with `ondelete="CASCADE"`).
        - When a Farm is deleted, all planted Crop entities on this parcel
          are cascaded and removed (`cascade="all, delete-orphan"`).
        - When a Farm is deleted, all recorded WeatherObservation entities on this parcel
          are cascaded and removed (`cascade="all, delete-orphan"`).
    """
    __tablename__ = "farms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    farmer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("farmers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    location: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    area: Mapped[float] = mapped_column(Float, nullable=False)
    area_unit: Mapped[str] = mapped_column(String(20), nullable=False, default="acre")

    # Relationships
    farmer: Mapped["Farmer"] = relationship("Farmer", back_populates="farms")
    crops: Mapped[List["Crop"]] = relationship(
        "Crop",
        back_populates="farm",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    weather_observations: Mapped[List["WeatherObservation"]] = relationship(
        "WeatherObservation",
        back_populates="farm",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Farm(id={self.id}, name='{self.name}', location='{self.location}', area={self.area} {self.area_unit})>"
