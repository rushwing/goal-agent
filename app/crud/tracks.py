from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.track_category import TrackCategory
from app.models.track_subcategory import TrackSubcategory


async def get_all_categories(db: AsyncSession) -> list[TrackCategory]:
    result = await db.execute(
        select(TrackCategory)
        .where(TrackCategory.is_active == True)  # noqa: E712
        .options(selectinload(TrackCategory.subcategories))
        .order_by(TrackCategory.sort_order)
    )
    return list(result.scalars().all())


async def get_subcategories(
    db: AsyncSession, *, category_id: int | None = None
) -> list[TrackSubcategory]:
    q = select(TrackSubcategory).where(TrackSubcategory.is_active == True)  # noqa: E712
    if category_id is not None:
        q = q.where(TrackSubcategory.category_id == category_id)
    q = q.order_by(TrackSubcategory.category_id, TrackSubcategory.sort_order)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_subcategory(db: AsyncSession, subcategory_id: int) -> TrackSubcategory | None:
    result = await db.execute(select(TrackSubcategory).where(TrackSubcategory.id == subcategory_id))
    return result.scalar_one_or_none()
