from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.plan import Plan, PlanStatus
from app.models.target import Target
from app.models.weekly_milestone import WeeklyMilestone
from app.models.task import Task
from app.schemas.plan import PlanCreate, PlanUpdate


class CRUDPlan(CRUDBase[Plan, PlanCreate, PlanUpdate]):
    async def get_with_milestones(self, db: AsyncSession, plan_id: int) -> Optional[Plan]:
        result = await db.execute(
            select(Plan)
            .options(selectinload(Plan.milestones).selectinload(WeeklyMilestone.tasks))
            .where(Plan.id == plan_id)
        )
        return result.scalar_one_or_none()

    async def get_by_go_getter(
        self, db: AsyncSession, go_getter_id: int, target_id: Optional[int] = None
    ) -> Sequence[Plan]:
        query = (
            select(Plan)
            .join(Target, Plan.target_id == Target.id)
            .where(Target.go_getter_id == go_getter_id)
        )
        if target_id:
            query = query.where(Plan.target_id == target_id)
        result = await db.execute(query)
        return result.scalars().all()

    async def get_active_for_go_getter(self, db: AsyncSession, go_getter_id: int) -> Optional[Plan]:
        result = await db.execute(
            select(Plan)
            .join(Target, Plan.target_id == Target.id)
            .where(Target.go_getter_id == go_getter_id, Plan.status == PlanStatus.active)
            .limit(1)
        )
        return result.scalar_one_or_none()


crud_plan = CRUDPlan(Plan)
