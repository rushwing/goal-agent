from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.best_pal import BestPal
from app.schemas.best_pal import BestPalCreate, BestPalUpdate


class CRUDBestPal(CRUDBase[BestPal, BestPalCreate, BestPalUpdate]):
    async def get_by_chat_id(self, db: AsyncSession, chat_id: int) -> Optional[BestPal]:
        result = await db.execute(select(BestPal).where(BestPal.telegram_chat_id == chat_id))
        return result.scalar_one_or_none()

    async def get_admins(self, db: AsyncSession) -> list[BestPal]:
        result = await db.execute(select(BestPal).where(BestPal.is_admin == True))
        return list(result.scalars().all())


crud_best_pal = CRUDBestPal(BestPal)
