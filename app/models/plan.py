from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, Enum, ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.target import Target
    from app.models.weekly_milestone import WeeklyMilestone

import enum


class PlanStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class Plan(Base, TimestampMixin):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_id: Mapped[int] = mapped_column(Integer, ForeignKey("targets.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    overview: Mapped[str] = mapped_column(Text, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_weeks: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[PlanStatus] = mapped_column(
        Enum(PlanStatus), nullable=False, default=PlanStatus.draft
    )
    github_commit_sha: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    github_file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    llm_prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    llm_completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    target: Mapped["Target"] = relationship("Target", back_populates="plans")
    milestones: Mapped[list["WeeklyMilestone"]] = relationship(
        "WeeklyMilestone", back_populates="plan", order_by="WeeklyMilestone.week_number"
    )
