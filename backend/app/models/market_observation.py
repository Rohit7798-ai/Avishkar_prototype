"""
Market Observation ORM domain model.
"""

from datetime import date
from sqlalchemy import Date, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class MarketObservation(Base, TimestampMixin):
    """
    Records empirical observed mandi market prices for a crop/commodity.
    Independent from a specific farm or farmer.
    Explicit units:
      - price: monetary value per specified unit (e.g. Rs/Quintal, Rs/kg)
    """
    __tablename__ = "market_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    crop_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    market_name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    observed_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<MarketObservation(id={self.id}, crop='{self.crop_name}', "
            f"market='{self.market_name}', date={self.observed_date}, price={self.price} {self.unit})>"
        )
