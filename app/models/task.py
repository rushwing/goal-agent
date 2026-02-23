import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.weekly_milestone import WeeklyMilestone
    from app.models.check_in import CheckIn


class TaskType(str, enum.Enum):
    reading = "reading"
    writing = "writing"
    math = "math"
    practice = "practice"
    review = "review"
    project = "project"
    quiz = "quiz"
    other = "other"


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    milestone_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("weekly_milestones.id"), nullable=False
    )
    day_of_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 0=Mon, 6=Sun
    sequence_in_day: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_minutes: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=30)
    xp_reward: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    task_type: Mapped[TaskType] = mapped_column(
        Enum(TaskType), nullable=False, default=TaskType.practice
    )
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    milestone: Mapped["WeeklyMilestone"] = relationship("WeeklyMilestone", back_populates="tasks")
    check_ins: Mapped[list["CheckIn"]] = relationship("CheckIn", back_populates="task")
