"""Tests for issue #16: checkin/skip task ownership and date eligibility validation."""

from datetime import date, timedelta

import pytest
import pytest_asyncio

from app.models.best_pal import BestPal
from app.models.go_getter import GoGetter
from app.models.target import Target, VacationType, TargetStatus
from app.models.plan import Plan, PlanStatus
from app.models.weekly_milestone import WeeklyMilestone
from app.models.task import Task, TaskType
from app.mcp.tools.checkin_tools import _validate_task


def _monday_of_current_week() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


@pytest_asyncio.fixture
async def two_go_getters_with_tasks(db):
    """Two go_getters each with a task scheduled for today, plus one task for a different day."""
    best_pal = BestPal(name="BestPal", telegram_chat_id=10000, is_admin=False)
    db.add(best_pal)
    await db.flush()

    go_getter_a = GoGetter(
        best_pal_id=best_pal.id,
        name="Alice",
        display_name="Alice",
        grade="5",
        telegram_chat_id=10001,
    )
    go_getter_b = GoGetter(
        best_pal_id=best_pal.id,
        name="Bob",
        display_name="Bob",
        grade="5",
        telegram_chat_id=10002,
    )
    db.add_all([go_getter_a, go_getter_b])
    await db.flush()

    today = date.today()
    week_start = _monday_of_current_week()
    week_end = week_start + timedelta(days=6)
    today_dow = today.weekday()
    other_dow = (today_dow + 1) % 7  # a different day of the week

    tasks = {}
    for key, go_getter in (("a", go_getter_a), ("b", go_getter_b)):
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
            total_tasks=2,
            completed_tasks=0,
        )
        db.add(milestone)
        await db.flush()

        task_today = Task(
            milestone_id=milestone.id,
            day_of_week=today_dow,
            sequence_in_day=1,
            title="Today Task",
            description="",
            estimated_minutes=30,
            xp_reward=10,
            task_type=TaskType.practice,
            is_optional=False,
        )
        task_other_day = Task(
            milestone_id=milestone.id,
            day_of_week=other_dow,
            sequence_in_day=1,
            title="Other Day Task",
            description="",
            estimated_minutes=30,
            xp_reward=10,
            task_type=TaskType.practice,
            is_optional=False,
        )
        db.add_all([task_today, task_other_day])
        tasks[key] = {"today": task_today, "other_day": task_other_day}

    await db.flush()
    await db.refresh(go_getter_a)
    await db.refresh(go_getter_b)
    return go_getter_a, go_getter_b, tasks


@pytest.mark.asyncio
async def test_validate_task_correct_owner_and_today(db, two_go_getters_with_tasks):
    """_validate_task succeeds for the correct owner's task scheduled today."""
    go_getter_a, _, tasks = two_go_getters_with_tasks
    task = await _validate_task(db, tasks["a"]["today"].id, go_getter_a.id)
    assert task is not None
    assert task.id == tasks["a"]["today"].id


@pytest.mark.asyncio
async def test_validate_task_wrong_go_getter_raises(db, two_go_getters_with_tasks):
    """checkin_task with another go_getter's task must raise ValueError."""
    go_getter_a, go_getter_b, tasks = two_go_getters_with_tasks
    with pytest.raises(ValueError, match="not found or not owned"):
        await _validate_task(db, tasks["a"]["today"].id, go_getter_b.id)


@pytest.mark.asyncio
async def test_validate_task_wrong_day_raises(db, two_go_getters_with_tasks):
    """checkin_task with a task not scheduled for today must raise ValueError."""
    go_getter_a, _, tasks = two_go_getters_with_tasks
    with pytest.raises(ValueError, match="not scheduled for today"):
        await _validate_task(db, tasks["a"]["other_day"].id, go_getter_a.id)


@pytest.mark.asyncio
async def test_skip_task_wrong_go_getter_raises(db, two_go_getters_with_tasks):
    """skip_task with another go_getter's task must raise ValueError."""
    _, go_getter_b, tasks = two_go_getters_with_tasks
    with pytest.raises(ValueError, match="not found or not owned"):
        await _validate_task(db, tasks["a"]["today"].id, go_getter_b.id)


@pytest.mark.asyncio
async def test_skip_task_wrong_day_raises(db, two_go_getters_with_tasks):
    """skip_task with a task not scheduled for today must raise ValueError."""
    go_getter_a, _, tasks = two_go_getters_with_tasks
    with pytest.raises(ValueError, match="not scheduled for today"):
        await _validate_task(db, tasks["a"]["other_day"].id, go_getter_a.id)
