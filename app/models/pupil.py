from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Boolean, Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.check_in import CheckIn
    from app.models.parent import Parent
    from app.models.target import Target
    from app.models.achievement import Achievement
    from app.models.notification import Notification
    from app.models.report import Report


class Pupil(Base, TimestampMixin):
    __tablename__ = "pupils"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("parents.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(50), nullable=False)
    grade: Mapped[str] = mapped_column(String(20), nullable=False)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    xp_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    streak_current: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    streak_longest: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    streak_last_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    parent: Mapped[Optional["Parent"]] = relationship("Parent", back_populates="children")
    targets: Mapped[list["Target"]] = relationship("Target", back_populates="pupil")
    check_ins: Mapped[list["CheckIn"]] = relationship("CheckIn", back_populates="pupil")
    achievements: Mapped[list["Achievement"]] = relationship("Achievement", back_populates="pupil")
    reports: Mapped[list["Report"]] = relationship("Report", back_populates="pupil")
