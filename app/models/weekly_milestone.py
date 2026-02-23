from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.plan import Plan
    from app.models.task import Task


class WeeklyMilestone(Base, TimestampMixin):
    __tablename__ = "weekly_milestones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("plans.id"), nullable=False)
    week_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_tasks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_tasks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    plan: Mapped["Plan"] = relationship("Plan", back_populates="milestones")
    tasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="milestone",
        order_by="(Task.day_of_week, Task.sequence_in_day)",
    )
