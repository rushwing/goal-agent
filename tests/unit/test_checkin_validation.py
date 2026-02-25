"""Tests for issue #1: check-in task ownership and date eligibility validation."""

from datetime import date, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.best_pal import BestPal
from app.models.go_getter import GoGetter
from app.models.target import Target, VacationType, TargetStatus
from app.models.plan import Plan, PlanStatus
from app.models.weekly_milestone import WeeklyMilestone
from app.models.task import Task, TaskType
from app.crud.tasks import crud_task


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _monday_of_current_week() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


@pytest_asyncio.fixture
async def family(db):
    """Minimal fixture: one best_pal, two go_getters, one plan each."""
    best_pal = BestPal(name="BestPal", telegram_chat_id=1000, is_admin=False)
    db.add(best_pal)
    await db.flush()

    go_getter_a = GoGetter(
        best_pal_id=best_pal.id,
        name="Alice",
        display_name="Alice",
        grade="5",
        telegram_chat_id=2001,
    )
    go_getter_b = GoGetter(
        best_pal_id=best_pal.id,
        name="Bob",
        display_name="Bob",
        grade="5",
        telegram_chat_id=2002,
    )
    db.add_all([go_getter_a, go_getter_b])
    await db.flush()

    today = date.today()
    week_start = _monday_of_current_week()
    week_end = week_start + timedelta(days=6)

    for go_getter in (go_getter_a, go_getter_b):
        target = Target(
            go_getter_id=go_getter.id,
            title="Math",
            subject="Math",
            description="",
            vacation_type=VacationType.summer,
            vacation_year=today.year,
            status=TargetStatus.active,
        )
        db.add(target)
        await db.flush()

        plan = Plan(
            target_id=target.id,
            title="Plan",
            overview="",
            start_date=week_start,
            end_date=week_end,
            total_weeks=1,
            status=PlanStatus.active,
        )
        db.add(plan)
        await db.flush()

        milestone = WeeklyMilestone(
            plan_id=plan.id,
            week_number=1,
            title="W1",
            description="",
            start_date=week_start,
            end_date=week_end,
            total_tasks=1,
            completed_tasks=0,
        )
        db.add(milestone)
        await db.flush()

        task = Task(
            milestone_id=milestone.id,
            day_of_week=today.weekday(),
            sequence_in_day=1,
            title="Task",
            description="",
            estimated_minutes=30,
            xp_reward=10,
            task_type=TaskType.practice,
            is_optional=False,
        )
        db.add(task)

    await db.flush()
    await db.refresh(go_getter_a)
    await db.refresh(go_getter_b)
    return go_getter_a, go_getter_b


@pytest.mark.asyncio
async def test_get_with_ownership_correct_go_getter(db, family):
    go_getter_a, go_getter_b = family
    tasks_a = await crud_task.get_tasks_for_day(db, go_getter_a.id, date.today())
    assert tasks_a, "Fixture must create a task for today"
    task = tasks_a[0]

    result = await crud_task.get_with_ownership(db, task.id, go_getter_a.id)
    assert result is not None
    assert result.id == task.id


@pytest.mark.asyncio
async def test_get_with_ownership_wrong_go_getter(db, family):
    """Cross-go_getter spoofing: task belongs to go_getter_a, go_getter_b tries to claim it."""
    go_getter_a, go_getter_b = family
    tasks_a = await crud_task.get_tasks_for_day(db, go_getter_a.id, date.today())
    task = tasks_a[0]

    result = await crud_task.get_with_ownership(db, task.id, go_getter_b.id)
    assert result is None, "Ownership check must reject cross-go_getter access"


@pytest.mark.asyncio
async def test_get_eligible_for_date_today(db, family):
    go_getter_a, _ = family
    tasks_a = await crud_task.get_tasks_for_day(db, go_getter_a.id, date.today())
    task = tasks_a[0]

    result = await crud_task.get_eligible_for_date(db, task.id, go_getter_a.id, date.today())
    assert result is not None


@pytest.mark.asyncio
async def test_get_eligible_for_date_wrong_day(db, family):
    """Task scheduled for today must not be eligible for tomorrow."""
    go_getter_a, _ = family
    tasks_a = await crud_task.get_tasks_for_day(db, go_getter_a.id, date.today())
    task = tasks_a[0]

    tomorrow = date.today() + timedelta(days=1)
    result = await crud_task.get_eligible_for_date(db, task.id, go_getter_a.id, tomorrow)
    assert result is None, "Date eligibility check must reject wrong day"
