from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.pupil import Pupil
from app.schemas.pupil import PupilCreate, PupilUpdate


class CRUDPupil(CRUDBase[Pupil, PupilCreate, PupilUpdate]):
    async def get_by_chat_id(self, db: AsyncSession, chat_id: int) -> Optional[Pupil]:
        result = await db.execute(select(Pupil).where(Pupil.telegram_chat_id == chat_id))
        return result.scalar_one_or_none()

    async def get_active(self, db: AsyncSession) -> Sequence[Pupil]:
        result = await db.execute(select(Pupil).where(Pupil.is_active == True))
        return result.scalars().all()

    async def get_by_parent(self, db: AsyncSession, parent_id: int) -> Sequence[Pupil]:
        result = await db.execute(select(Pupil).where(Pupil.parent_id == parent_id))
        return result.scalars().all()

    async def create(self, db: AsyncSession, *, obj_in: PupilCreate) -> Pupil:
        data = obj_in.model_dump()  # parent_id is now persisted
        db_obj = Pupil(**data)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj


crud_pupil = CRUDPupil(Pupil)
