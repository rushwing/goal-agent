from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.goal_group import ChangeType, GoalGroup, GoalGroupChange, ReplanStatus


async def get(db: AsyncSession, group_id: int) -> Optional[GoalGroup]:
    result = await db.execute(
        select(GoalGroup)
        .where(GoalGroup.id == group_id)
        .options(selectinload(GoalGroup.targets), selectinload(GoalGroup.changes))
    )
    return result.scalar_one_or_none()


async def get_active_for_go_getter(
    db: AsyncSession, go_getter_id: int
) -> Optional[GoalGroup]:
    """Return the single active GoalGroup for a GoGetter, if any."""
    result = await db.execute(
        select(GoalGroup)
        .where(GoalGroup.go_getter_id == go_getter_id, GoalGroup.status == "active")
        .options(selectinload(GoalGroup.targets))
    )
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession,
    *,
    go_getter_id: int,
    title: str,
    description: Optional[str] = None,
    start_date=None,
    end_date=None,
) -> GoalGroup:
    group = GoalGroup(
        go_getter_id=go_getter_id,
        title=title,
        description=description,
        start_date=start_date,
        end_date=end_date,
    )
    db.add(group)
    await db.flush()
    await db.refresh(group)
    return group


async def record_change(
    db: AsyncSession,
    *,
    group: GoalGroup,
    change_type: ChangeType,
    target_id: Optional[int] = None,
    old_value: Optional[dict] = None,
    new_value: Optional[dict] = None,
) -> GoalGroupChange:
    """Record a structural change and update last_change_at on the group."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    change = GoalGroupChange(
        group_id=group.id,
        change_type=change_type,
        target_id=target_id,
        old_value=old_value,
        new_value=new_value,
    )
    db.add(change)
    group.last_change_at = now
    db.add(group)
    await db.flush()
    await db.refresh(change)
    return change


async def acquire_replan_lock(db: AsyncSession, group_id: int) -> bool:
    """Atomically set replan_status idle → in_progress.

    Returns True if the lock was acquired, False if already in_progress.
    """
    result = await db.execute(
        update(GoalGroup)
        .where(GoalGroup.id == group_id, GoalGroup.replan_status == ReplanStatus.idle)
        .values(replan_status=ReplanStatus.in_progress)
    )
    await db.flush()
    return result.rowcount == 1


async def release_replan_lock(
    db: AsyncSession, group_id: int, *, failed: bool = False
) -> None:
    status = ReplanStatus.failed if failed else ReplanStatus.idle
    await db.execute(
        update(GoalGroup)
        .where(GoalGroup.id == group_id)
        .values(replan_status=status)
    )
    await db.flush()
