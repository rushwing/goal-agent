import enum
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.go_getter import GoGetter
    from app.models.target import Target


class GoalGroupStatus(str, enum.Enum):
    active = "active"
    completed = "completed"
    archived = "archived"


class ReplanStatus(str, enum.Enum):
    idle = "idle"
    in_progress = "in_progress"
    failed = "failed"


class ChangeType(str, enum.Enum):
    target_added = "target_added"
    target_removed = "target_removed"
    target_paused = "target_paused"
    priority_changed = "priority_changed"
    end_date_extended = "end_date_extended"


class GoalGroup(Base, TimestampMixin):
    __tablename__ = "goal_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    go_getter_id: Mapped[int] = mapped_column(Integer, ForeignKey("go_getters.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[GoalGroupStatus] = mapped_column(
        Enum(GoalGroupStatus), nullable=False, default=GoalGroupStatus.active
    )
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    # Rolling 7-day change limit: checked before any structural modification
    last_change_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # Optimistic lock for concurrent re-planning guard
    replan_status: Mapped[ReplanStatus] = mapped_column(
        Enum(ReplanStatus), nullable=False, default=ReplanStatus.idle
    )

    go_getter: Mapped["GoGetter"] = relationship("GoGetter", back_populates="goal_groups")
    targets: Mapped[list["Target"]] = relationship("Target", back_populates="group")
    changes: Mapped[list["GoalGroupChange"]] = relationship(
        "GoalGroupChange", back_populates="group", order_by="GoalGroupChange.created_at"
    )


class GoalGroupChange(Base):
    """Audit log for structural changes to a GoalGroup.

    Each row represents one user-initiated change (target added/removed/etc.).
    Used to enforce the rolling-7-day change limit.
    """

    __tablename__ = "goal_group_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("goal_groups.id"), nullable=False)
    change_type: Mapped[ChangeType] = mapped_column(Enum(ChangeType), nullable=False)
    target_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("targets.id"), nullable=True
    )
    old_value: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    new_value: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    triggered_replan_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    replan_plan_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default="now()", nullable=False
    )

    group: Mapped["GoalGroup"] = relationship("GoalGroup", back_populates="changes")
    target: Mapped[Optional["Target"]] = relationship("Target")
