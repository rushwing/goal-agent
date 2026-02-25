from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.achievement import Achievement
from app.schemas.achievement import AchievementResponse


class CRUDAchievement(CRUDBase[Achievement, AchievementResponse, AchievementResponse]):
    async def get_by_go_getter(self, db: AsyncSession, go_getter_id: int) -> Sequence[Achievement]:
        result = await db.execute(
            select(Achievement).where(Achievement.go_getter_id == go_getter_id)
        )
        return result.scalars().all()

    async def get_by_badge(
        self, db: AsyncSession, go_getter_id: int, badge_key: str
    ) -> Optional[Achievement]:
        result = await db.execute(
            select(Achievement).where(
                Achievement.go_getter_id == go_getter_id,
                Achievement.badge_key == badge_key,
            )
        )
        return result.scalar_one_or_none()

    async def has_badge(self, db: AsyncSession, go_getter_id: int, badge_key: str) -> bool:
        result = await self.get_by_badge(db, go_getter_id, badge_key)
        return result is not None


crud_achievement = CRUDAchievement(Achievement)
