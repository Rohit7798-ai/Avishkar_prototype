"""
Farmer ORM domain model.
"""

from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.farm import Farm


class Farmer(Base, TimestampMixin):
    """
    Farmer entity representing the primary farm owner/operator.

    Cascading Behavior:
        - When a Farmer is deleted, all associated Farm entities (and recursively
          their Crop entities) are cascaded and removed (`cascade="all, delete-orphan"`).
    """
    __tablename__ = "farmers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(25), nullable=True)

    # Relationships: One-to-Many with Farm
    farms: Mapped[List["Farm"]] = relationship(
        "Farm",
        back_populates="farmer",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Farmer(id={self.id}, name='{self.name}', phone='{self.phone}')>"
