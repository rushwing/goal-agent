from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.target import Target, TargetStatus
from app.schemas.target import TargetCreate, TargetUpdate


class CRUDTarget(CRUDBase[Target, TargetCreate, TargetUpdate]):
    async def get_by_go_getter(self, db: AsyncSession, go_getter_id: int) -> Sequence[Target]:
        result = await db.execute(select(Target).where(Target.go_getter_id == go_getter_id))
        return result.scalars().all()

    async def get_active_by_go_getter(
        self, db: AsyncSession, go_getter_id: int
    ) -> Sequence[Target]:
        result = await db.execute(
            select(Target).where(
                Target.go_getter_id == go_getter_id, Target.status == TargetStatus.active
            )
        )
        return result.scalars().all()


crud_target = CRUDTarget(Target)
