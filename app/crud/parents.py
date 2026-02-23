from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.parent import Parent
from app.schemas.parent import ParentCreate, ParentUpdate


class CRUDParent(CRUDBase[Parent, ParentCreate, ParentUpdate]):
    async def get_by_chat_id(self, db: AsyncSession, chat_id: int) -> Optional[Parent]:
        result = await db.execute(select(Parent).where(Parent.telegram_chat_id == chat_id))
        return result.scalar_one_or_none()

    async def get_admins(self, db: AsyncSession) -> list[Parent]:
        result = await db.execute(select(Parent).where(Parent.is_admin == True))
        return list(result.scalars().all())


crud_parent = CRUDParent(Parent)
