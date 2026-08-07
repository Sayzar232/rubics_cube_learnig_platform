from __future__ import annotations

from enum import Enum

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, CreatedAtMixin


class AlgorithmCategory(str, Enum):
    OLL = "OLL"
    PLL = "PLL"


class Algorithm(Base, CreatedAtMixin):
    __tablename__ = "algorithms"
    __table_args__ = (
        UniqueConstraint("category", "name", name="uq_algorithms_category_name"),
        UniqueConstraint("category", "algorithm_number", name="uq_algorithms_category_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[AlgorithmCategory] = mapped_column(
        SqlEnum(AlgorithmCategory, native_enum=False, length=10),
        nullable=False,
        index=True,
    )
    algorithm_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    group: Mapped[str] = mapped_column(String(100), nullable=False)
    formula: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    progress = relationship("UserProgress", back_populates="algorithm", cascade="all, delete-orphan")
