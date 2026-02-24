"""Tests for issue #1: check-in task ownership and date eligibility validation."""

from datetime import date, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.parent import Parent
from app.models.pupil import Pupil
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
    """Minimal fixture: one parent, two pupils, one plan each."""
    parent = Parent(name="Parent", telegram_chat_id=1000, is_admin=False)
    db.add(parent)
    await db.flush()

    pupil_a = Pupil(
        parent_id=parent.id,
        name="Alice",
        display_name="Alice",
        grade="5",
        telegram_chat_id=2001,
    )
    pupil_b = Pupil(
        parent_id=parent.id,
        name="Bob",
        display_name="Bob",
        grade="5",
        telegram_chat_id=2002,
    )
    db.add_all([pupil_a, pupil_b])
    await db.flush()

    today = date.today()
    week_start = _monday_of_current_week()
    week_end = week_start + timedelta(days=6)

    for pupil in (pupil_a, pupil_b):
        target = Target(
            pupil_id=pupil.id,
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
    await db.refresh(pupil_a)
    await db.refresh(pupil_b)
    return pupil_a, pupil_b


@pytest.mark.asyncio
async def test_get_with_ownership_correct_pupil(db, family):
    pupil_a, pupil_b = family
    tasks_a = await crud_task.get_tasks_for_day(db, pupil_a.id, date.today())
    assert tasks_a, "Fixture must create a task for today"
    task = tasks_a[0]

    result = await crud_task.get_with_ownership(db, task.id, pupil_a.id)
    assert result is not None
    assert result.id == task.id


@pytest.mark.asyncio
async def test_get_with_ownership_wrong_pupil(db, family):
    """Cross-pupil spoofing: task belongs to pupil_a, pupil_b tries to claim it."""
    pupil_a, pupil_b = family
    tasks_a = await crud_task.get_tasks_for_day(db, pupil_a.id, date.today())
    task = tasks_a[0]

    result = await crud_task.get_with_ownership(db, task.id, pupil_b.id)
    assert result is None, "Ownership check must reject cross-pupil access"


@pytest.mark.asyncio
async def test_get_eligible_for_date_today(db, family):
    pupil_a, _ = family
    tasks_a = await crud_task.get_tasks_for_day(db, pupil_a.id, date.today())
    task = tasks_a[0]

    result = await crud_task.get_eligible_for_date(db, task.id, pupil_a.id, date.today())
    assert result is not None


@pytest.mark.asyncio
async def test_get_eligible_for_date_wrong_day(db, family):
    """Task scheduled for today must not be eligible for tomorrow."""
    pupil_a, _ = family
    tasks_a = await crud_task.get_tasks_for_day(db, pupil_a.id, date.today())
    task = tasks_a[0]

    tomorrow = date.today() + timedelta(days=1)
    result = await crud_task.get_eligible_for_date(db, task.id, pupil_a.id, tomorrow)
    assert result is None, "Date eligibility check must reject wrong day"
