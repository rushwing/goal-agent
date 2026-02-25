from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.go_getter import GoGetter


class Achievement(Base, TimestampMixin):
    __tablename__ = "achievements"
    __table_args__ = (
        UniqueConstraint("go_getter_id", "badge_key", name="uq_achievement_go_getter_badge"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    go_getter_id: Mapped[int] = mapped_column(Integer, ForeignKey("go_getters.id"), nullable=False)
    badge_key: Mapped[str] = mapped_column(String(50), nullable=False)
    badge_name: Mapped[str] = mapped_column(String(100), nullable=False)
    badge_icon: Mapped[str] = mapped_column(String(10), nullable=False)  # emoji
    xp_bonus: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    go_getter: Mapped["GoGetter"] = relationship("GoGetter", back_populates="achievements")
