"""CRUD helpers for GoalGroupWizard."""

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.goal_group_wizard import GoalGroupWizard, WizardStatus, TERMINAL_STATUSES


async def create(
    db: AsyncSession,
    *,
    go_getter_id: int,
    expires_at: datetime,
) -> GoalGroupWizard:
    wizard = GoalGroupWizard(
        go_getter_id=go_getter_id,
        status=WizardStatus.collecting_scope,
        expires_at=expires_at,
    )
    db.add(wizard)
    await db.flush()
    await db.refresh(wizard)
    return wizard


async def get(db: AsyncSession, wizard_id: int) -> Optional[GoalGroupWizard]:
    result = await db.execute(select(GoalGroupWizard).where(GoalGroupWizard.id == wizard_id))
    return result.scalar_one_or_none()


async def get_active_for_go_getter(
    db: AsyncSession, go_getter_id: int
) -> Optional[GoalGroupWizard]:
    """Return the active wizard for a go_getter (excludes terminal statuses), if any."""
    terminal_values = [s.value for s in TERMINAL_STATUSES]
    result = await db.execute(
        select(GoalGroupWizard)
        .where(
            GoalGroupWizard.go_getter_id == go_getter_id,
            GoalGroupWizard.status.notin_(terminal_values),
        )
        .order_by(GoalGroupWizard.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def update_wizard(db: AsyncSession, wizard: GoalGroupWizard, **fields) -> GoalGroupWizard:
    """Generic patch: set attributes + flush + refresh."""
    for key, value in fields.items():
        setattr(wizard, key, value)
    db.add(wizard)
    await db.flush()
    await db.refresh(wizard)
    return wizard


async def expire_stale(db: AsyncSession) -> int:
    """Set status=cancelled for wizards past expires_at that are not in terminal state.

    Returns the number of wizards cancelled.
    """
    now = datetime.now(UTC).replace(tzinfo=None)
    terminal_values = [s.value for s in TERMINAL_STATUSES]
    result = await db.execute(
        update(GoalGroupWizard)
        .where(
            GoalGroupWizard.expires_at < now,
            GoalGroupWizard.status.notin_(terminal_values),
        )
        .values(status=WizardStatus.cancelled)
    )
    await db.flush()
    return result.rowcount
