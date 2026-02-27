import enum
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, JSON, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.go_getter import GoGetter
    from app.models.goal_group import GoalGroup


class WizardStatus(str, enum.Enum):
    collecting_scope = "collecting_scope"
    collecting_targets = "collecting_targets"
    collecting_constraints = "collecting_constraints"
    generating_plans = "generating_plans"
    feasibility_check = "feasibility_check"
    adjusting = "adjusting"
    confirmed = "confirmed"
    cancelled = "cancelled"
    failed = "failed"


TERMINAL_STATUSES: frozenset[WizardStatus] = frozenset(
    {WizardStatus.confirmed, WizardStatus.cancelled, WizardStatus.failed}
)


class GoalGroupWizard(Base, TimestampMixin):
    __tablename__ = "goal_group_wizards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    go_getter_id: Mapped[int] = mapped_column(Integer, ForeignKey("go_getters.id"), nullable=False)
    status: Mapped[WizardStatus] = mapped_column(
        Enum(WizardStatus), nullable=False, default=WizardStatus.collecting_scope
    )
    group_title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    group_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    # [{target_id, subcategory_id, priority}]
    target_specs: Mapped[Optional[list[Any]]] = mapped_column(JSON, nullable=True)
    # {str(subcategory_id): {daily_minutes, preferred_days}}
    constraints: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    # [plan_id, ...]
    draft_plan_ids: Mapped[Optional[list[int]]] = mapped_column(JSON, nullable=True)
    # 1 = passed, 0 = failed (has blockers), NULL = not yet checked
    feasibility_passed: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    # [{rule_code, level, subcategory_id, detail, llm_explanation, is_blocker}]
    feasibility_risks: Mapped[Optional[list[Any]]] = mapped_column(JSON, nullable=True)
    goal_group_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("goal_groups.id"), nullable=True
    )
    generation_errors: Mapped[Optional[list[Any]]] = mapped_column(JSON, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    go_getter: Mapped["GoGetter"] = relationship("GoGetter")
    goal_group: Mapped[Optional["GoalGroup"]] = relationship("GoalGroup")
