from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.target import Target
    from app.models.track_category import TrackCategory


class TrackSubcategory(Base, TimestampMixin):
    __tablename__ = "track_subcategories"
    __table_args__ = (
        UniqueConstraint("category_id", "name", name="uq_track_subcategory_cat_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("track_categories.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    category: Mapped["TrackCategory"] = relationship("TrackCategory", back_populates="subcategories")
    targets: Mapped[list["Target"]] = relationship("Target", back_populates="subcategory")
