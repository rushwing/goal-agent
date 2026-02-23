import enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Enum,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.task import Task
    from app.models.pupil import Pupil


class CheckInStatus(str, enum.Enum):
    completed = "completed"
    skipped = "skipped"


class CheckIn(Base, TimestampMixin):
    __tablename__ = "check_ins"
    __table_args__ = (UniqueConstraint("task_id", "pupil_id", name="uq_checkin_task_pupil"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("tasks.id"), nullable=False)
    pupil_id: Mapped[int] = mapped_column(Integer, ForeignKey("pupils.id"), nullable=False)
    status: Mapped[CheckInStatus] = mapped_column(
        Enum(CheckInStatus), nullable=False, default=CheckInStatus.completed
    )
    mood_score: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)  # 1-5
    duration_minutes: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    xp_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    streak_at_checkin: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    praise_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    skip_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="check_ins")
    pupil: Mapped["Pupil"] = relationship("Pupil", back_populates="check_ins")
