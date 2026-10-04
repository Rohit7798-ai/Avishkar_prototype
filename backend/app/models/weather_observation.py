"""
Weather Observation ORM domain model.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.farm import Farm


class WeatherObservation(Base, TimestampMixin):
    """
    Records empirical weather measurements associated with a farm location.
    Explicit units:
      - temperature: Celsius (°C)
      - humidity: percentage (%)
      - rainfall: millimeters (mm)
      - wind_speed: kilometers per hour (km/h)
    """
    __tablename__ = "weather_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    farm_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("farms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    temperature: Mapped[float] = mapped_column(Float, nullable=False)
    humidity: Mapped[float] = mapped_column(Float, nullable=False)
    rainfall: Mapped[float] = mapped_column(Float, nullable=False)
    wind_speed: Mapped[float] = mapped_column(Float, nullable=False)

    # Relationships
    farm: Mapped["Farm"] = relationship("Farm", back_populates="weather_observations")

    def __repr__(self) -> str:
        return (
            f"<WeatherObservation(id={self.id}, farm_id={self.farm_id}, "
            f"observed_at={self.observed_at}, temp={self.temperature}°C, rainfall={self.rainfall}mm)>"
        )
