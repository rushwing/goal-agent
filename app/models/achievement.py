from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.pupil import Pupil


class Achievement(Base, TimestampMixin):
    __tablename__ = "achievements"
    __table_args__ = (UniqueConstraint("pupil_id", "badge_key", name="uq_achievement_pupil_badge"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pupil_id: Mapped[int] = mapped_column(Integer, ForeignKey("pupils.id"), nullable=False)
    badge_key: Mapped[str] = mapped_column(String(50), nullable=False)
    badge_name: Mapped[str] = mapped_column(String(100), nullable=False)
    badge_icon: Mapped[str] = mapped_column(String(10), nullable=False)  # emoji
    xp_bonus: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    pupil: Mapped["Pupil"] = relationship("Pupil", back_populates="achievements")
