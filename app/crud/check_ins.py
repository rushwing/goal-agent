from datetime import date
from typing import Optional, Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.check_in import CheckIn, CheckInStatus
from app.models.task import Task
from app.models.weekly_milestone import WeeklyMilestone
from app.models.plan import Plan, PlanStatus
from app.models.target import Target
from app.schemas.check_in import CheckInCreate, CheckInResponse


class CRUDCheckIn(CRUDBase[CheckIn, CheckInCreate, CheckInResponse]):
    async def get_by_task_and_pupil(
        self, db: AsyncSession, task_id: int, pupil_id: int
    ) -> Optional[CheckIn]:
        result = await db.execute(
            select(CheckIn).where(
                CheckIn.task_id == task_id, CheckIn.pupil_id == pupil_id
            )
        )
        return result.scalar_one_or_none()

    async def get_completed_for_period(
        self, db: AsyncSession, pupil_id: int, start: date, end: date
    ) -> Sequence[CheckIn]:
        result = await db.execute(
            select(CheckIn)
            .join(Task, CheckIn.task_id == Task.id)
            .join(WeeklyMilestone, Task.milestone_id == WeeklyMilestone.id)
            .where(
                CheckIn.pupil_id == pupil_id,
                CheckIn.status == CheckInStatus.completed,
                WeeklyMilestone.start_date <= end,
                WeeklyMilestone.end_date >= start,
            )
        )
        return result.scalars().all()

    async def count_completed_today(
        self, db: AsyncSession, pupil_id: int, today: date
    ) -> int:
        result = await db.execute(
            select(func.count(CheckIn.id))
            .join(Task, CheckIn.task_id == Task.id)
            .join(WeeklyMilestone, Task.milestone_id == WeeklyMilestone.id)
            .where(
                CheckIn.pupil_id == pupil_id,
                CheckIn.status == CheckInStatus.completed,
                WeeklyMilestone.start_date <= today,
                WeeklyMilestone.end_date >= today,
                Task.day_of_week == today.weekday(),
            )
        )
        return result.scalar_one()


crud_check_in = CRUDCheckIn(CheckIn)
