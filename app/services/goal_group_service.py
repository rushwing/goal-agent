"""GoalGroup service: constraint enforcement and dynamic re-planning orchestration."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud import goal_groups as crud_gg
from app.models.goal_group import ChangeType, GoalGroup, GoalGroupChange
from app.models.plan import Plan, PlanStatus
from app.models.target import Target, TargetStatus
from app.models.task import Task, TaskStatus
from app.models.weekly_milestone import WeeklyMilestone

logger = logging.getLogger(__name__)

_CHANGE_COOLDOWN_DAYS = 7


# ---------------------------------------------------------------------------
# Constraint helpers
# ---------------------------------------------------------------------------


def _now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def assert_change_allowed(group: GoalGroup) -> None:
    """Raise ValueError if the rolling 7-day change limit has been hit."""
    if group.last_change_at is None:
        return
    elapsed = _now_utc() - group.last_change_at
    if elapsed < timedelta(days=_CHANGE_COOLDOWN_DAYS):
        remaining = timedelta(days=_CHANGE_COOLDOWN_DAYS) - elapsed
        hours = int(remaining.total_seconds() // 3600)
        raise ValueError(
            f"GoalGroup was already changed recently. "
            f"Next change allowed in {hours} hours."
        )


async def assert_subcategory_available(
    db: AsyncSession,
    *,
    go_getter_id: int,
    subcategory_id: int,
    exclude_target_id: Optional[int] = None,
) -> None:
    """Raise ValueError if the go_getter already has an active plan in this subcategory.

    MariaDB has no partial unique index, so we enforce this at the service layer.
    """
    q = (
        select(Plan)
        .join(Target, Plan.target_id == Target.id)
        .where(
            Target.go_getter_id == go_getter_id,
            Target.subcategory_id == subcategory_id,
            Target.status == TargetStatus.active,
            Plan.status == PlanStatus.active,
        )
    )
    if exclude_target_id is not None:
        q = q.where(Target.id != exclude_target_id)
    result = await db.execute(q)
    if result.scalar_one_or_none() is not None:
        raise ValueError(
            "An active plan already exists for this track subcategory. "
            "Complete or cancel the existing plan before starting a new one."
        )


# ---------------------------------------------------------------------------
# Re-planning
# ---------------------------------------------------------------------------


def _next_monday(from_date: datetime) -> datetime:
    """Return the Monday of the week after from_date's ISO week."""
    days_until_monday = (7 - from_date.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    return (from_date + timedelta(days=days_until_monday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


async def _supersede_future_tasks(db: AsyncSession, plan: Plan) -> None:
    """Mark all active tasks in future weeks as superseded.

    Current ISO week's tasks are left untouched (freeze rule).
    """
    replan_from = _next_monday(_now_utc()).date()

    for milestone in plan.milestones:
        if milestone.start_date >= replan_from:
            # Entire milestone is in the future — supersede all active tasks
            await db.execute(
                Task.__table__.update()
                .where(
                    Task.milestone_id == milestone.id,
                    Task.status == TaskStatus.active,
                )
                .values(status=TaskStatus.superseded)
            )
        # Milestones overlapping the current week are left intact


async def trigger_replan(
    db: AsyncSession,
    *,
    group: GoalGroup,
    change: GoalGroupChange,
) -> None:
    """Orchestrate atomic re-planning for all active targets in a GoalGroup.

    Flow:
      1. Acquire optimistic lock (idle → in_progress)
      2. For each active Target in group: supersede future tasks of current active Plan
      3. Generate new Plan per Target (draft status)
      4. Swap: new Plan → active, old Plan → superseded
      5. Release lock (idle)
      On any error: release lock as failed, re-raise.
    """
    from app.services import plan_generator  # avoid circular import

    acquired = await crud_gg.acquire_replan_lock(db, group.id)
    if not acquired:
        logger.warning(
            "GoalGroup %d re-plan skipped: another re-plan already in progress", group.id
        )
        return

    try:
        replan_from = _next_monday(_now_utc()).date()

        # Reload group with all relationships
        result = await db.execute(
            select(GoalGroup)
            .where(GoalGroup.id == group.id)
            .options(
                selectinload(GoalGroup.targets).selectinload(Target.plans)
            )
        )
        group = result.scalar_one()

        new_plan_ids: list[int] = []

        for target in group.targets:
            if target.status != TargetStatus.active:
                continue

            # Find the currently active plan for this target
            active_plan: Optional[Plan] = next(
                (p for p in target.plans if p.status == PlanStatus.active), None
            )

            if active_plan is None:
                continue

            # Load milestones + tasks for superseding
            result = await db.execute(
                select(Plan)
                .where(Plan.id == active_plan.id)
                .options(selectinload(Plan.milestones).selectinload(WeeklyMilestone.tasks))
            )
            active_plan_full = result.scalar_one()
            await _supersede_future_tasks(db, active_plan_full)

            if group.end_date and replan_from > group.end_date:
                # No future weeks left; just supersede, don't generate
                active_plan.status = PlanStatus.cancelled
                db.add(active_plan)
                continue

            # Generate new plan for the remaining window
            go_getter = group.go_getter
            new_plan = await plan_generator.generate_plan(
                db=db,
                target=target,
                pupil_name=go_getter.name,
                grade=go_getter.grade,
                start_date=replan_from,
                end_date=group.end_date or active_plan_full.end_date,
                daily_study_minutes=None,   # inherit from original or LLM decides
                preferred_days=None,
                extra_instructions=(
                    f"This is a re-plan triggered by a group change: "
                    f"{change.change_type.value}. "
                    f"Maintain continuity with the previous plan."
                ),
                initial_status=PlanStatus.draft,
            )
            new_plan.version = active_plan_full.version + 1
            new_plan.group_id = group.id
            db.add(new_plan)
            await db.flush()

            # Atomic swap
            active_plan_full.status = PlanStatus.cancelled
            active_plan_full.superseded_by_id = new_plan.id
            db.add(active_plan_full)

            new_plan.status = PlanStatus.active
            db.add(new_plan)
            await db.flush()

            new_plan_ids.append(new_plan.id)

        # Record replan completion on change log
        change.triggered_replan_at = _now_utc()
        if new_plan_ids:
            change.replan_plan_id = new_plan_ids[0]  # primary new plan for reference
        db.add(change)
        await db.flush()

        await crud_gg.release_replan_lock(db, group.id)
        logger.info("GoalGroup %d re-plan complete, new plans: %s", group.id, new_plan_ids)

    except Exception:
        await crud_gg.release_replan_lock(db, group.id, failed=True)
        raise


# ---------------------------------------------------------------------------
# High-level operations (called from API layer)
# ---------------------------------------------------------------------------


async def add_target_to_group(
    db: AsyncSession, *, group: GoalGroup, target: Target
) -> GoalGroupChange:
    """Validate constraints, attach target, record change, trigger re-plan."""
    await assert_change_allowed(group)

    if target.subcategory_id:
        await assert_subcategory_available(
            db, go_getter_id=group.go_getter_id, subcategory_id=target.subcategory_id
        )

    target.group_id = group.id
    db.add(target)
    await db.flush()

    change = await crud_gg.record_change(
        db,
        group=group,
        change_type=ChangeType.target_added,
        target_id=target.id,
        new_value={"target_title": target.title},
    )

    await trigger_replan(db, group=group, change=change)
    return change


async def remove_target_from_group(
    db: AsyncSession, *, group: GoalGroup, target: Target
) -> GoalGroupChange:
    """Cancel target, supersede its future tasks, trigger re-plan for remaining targets."""
    await assert_change_allowed(group)

    # Cancel the target and its active plan
    target.status = TargetStatus.cancelled
    db.add(target)

    active_plan: Optional[Plan] = None
    result = await db.execute(
        select(Plan)
        .where(Plan.target_id == target.id, Plan.status == PlanStatus.active)
        .options(selectinload(Plan.milestones).selectinload(WeeklyMilestone.tasks))
    )
    active_plan = result.scalar_one_or_none()
    if active_plan:
        await _supersede_future_tasks(db, active_plan)
        active_plan.status = PlanStatus.cancelled
        db.add(active_plan)

    await db.flush()

    change = await crud_gg.record_change(
        db,
        group=group,
        change_type=ChangeType.target_removed,
        target_id=target.id,
        old_value={"target_title": target.title},
    )

    # Re-plan remaining active targets to redistribute capacity
    await trigger_replan(db, group=group, change=change)
    return change
