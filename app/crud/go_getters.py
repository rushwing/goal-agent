from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.go_getter import GoGetter
from app.schemas.go_getter import GoGetterCreate, GoGetterUpdate


class CRUDGoGetter(CRUDBase[GoGetter, GoGetterCreate, GoGetterUpdate]):
    async def get_by_chat_id(self, db: AsyncSession, chat_id: int) -> Optional[GoGetter]:
        result = await db.execute(select(GoGetter).where(GoGetter.telegram_chat_id == chat_id))
        return result.scalar_one_or_none()

    async def get_active(self, db: AsyncSession) -> Sequence[GoGetter]:
        result = await db.execute(select(GoGetter).where(GoGetter.is_active == True))
        return result.scalars().all()

    async def get_by_best_pal(self, db: AsyncSession, best_pal_id: int) -> Sequence[GoGetter]:
        result = await db.execute(select(GoGetter).where(GoGetter.best_pal_id == best_pal_id))
        return result.scalars().all()

    async def create(self, db: AsyncSession, *, obj_in: GoGetterCreate) -> GoGetter:
        data = obj_in.model_dump()  # best_pal_id is now persisted
        db_obj = GoGetter(**data)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj


crud_go_getter = CRUDGoGetter(GoGetter)
