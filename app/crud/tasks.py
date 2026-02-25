from datetime import date
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.task import Task
from app.models.weekly_milestone import WeeklyMilestone
from app.models.plan import Plan, PlanStatus
from app.models.target import Target
from app.schemas.task import TaskBase


class CRUDTask(CRUDBase[Task, TaskBase, TaskBase]):
    async def get_tasks_for_day(
        self, db: AsyncSession, go_getter_id: int, target_date: date
    ) -> Sequence[Task]:
        """Get all tasks for a go getter on a specific date."""
        day_of_week = target_date.weekday()  # 0=Mon
        result = await db.execute(
            select(Task)
            .join(WeeklyMilestone, Task.milestone_id == WeeklyMilestone.id)
            .join(Plan, WeeklyMilestone.plan_id == Plan.id)
            .join(Target, Plan.target_id == Target.id)
            .where(
                Target.go_getter_id == go_getter_id,
                Plan.status == PlanStatus.active,
                WeeklyMilestone.start_date <= target_date,
                WeeklyMilestone.end_date >= target_date,
                Task.day_of_week == day_of_week,
            )
            .order_by(Task.sequence_in_day)
        )
        return result.scalars().all()

    async def get_tasks_for_week(
        self, db: AsyncSession, go_getter_id: int, week_start: date, week_end: date
    ) -> Sequence[Task]:
        result = await db.execute(
            select(Task)
            .join(WeeklyMilestone, Task.milestone_id == WeeklyMilestone.id)
            .join(Plan, WeeklyMilestone.plan_id == Plan.id)
            .join(Target, Plan.target_id == Target.id)
            .where(
                Target.go_getter_id == go_getter_id,
                Plan.status == PlanStatus.active,
                WeeklyMilestone.start_date <= week_end,
                WeeklyMilestone.end_date >= week_start,
            )
            .order_by(Task.day_of_week, Task.sequence_in_day)
        )
        return result.scalars().all()

    async def get_with_ownership(
        self, db: AsyncSession, task_id: int, go_getter_id: int
    ) -> Optional[Task]:
        """Return task if it belongs to the given go getter (via Target), ignoring date/status."""
        result = await db.execute(
            select(Task)
            .join(WeeklyMilestone, Task.milestone_id == WeeklyMilestone.id)
            .join(Plan, WeeklyMilestone.plan_id == Plan.id)
            .join(Target, Plan.target_id == Target.id)
            .where(Task.id == task_id, Target.go_getter_id == go_getter_id)
        )
        return result.scalar_one_or_none()

    async def get_eligible_for_date(
        self, db: AsyncSession, task_id: int, go_getter_id: int, check_date: date
    ) -> Optional[Task]:
        """Return task if it belongs to the go getter and is scheduled for check_date."""
        day_of_week = check_date.weekday()
        result = await db.execute(
            select(Task)
            .join(WeeklyMilestone, Task.milestone_id == WeeklyMilestone.id)
            .join(Plan, WeeklyMilestone.plan_id == Plan.id)
            .join(Target, Plan.target_id == Target.id)
            .where(
                Task.id == task_id,
                Target.go_getter_id == go_getter_id,
                Plan.status == PlanStatus.active,
                WeeklyMilestone.start_date <= check_date,
                WeeklyMilestone.end_date >= check_date,
                Task.day_of_week == day_of_week,
            )
        )
        return result.scalar_one_or_none()


crud_task = CRUDTask(Task)
