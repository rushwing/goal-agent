"""Tests for issue #4: single active plan invariant per go getter."""

from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from app.models.best_pal import BestPal
from app.models.go_getter import GoGetter
from app.models.target import Target, VacationType, TargetStatus
from app.models.plan import Plan, PlanStatus
from app.crud.plans import crud_plan


@pytest_asyncio.fixture
async def go_getter_with_target(db):
    best_pal = BestPal(name="P", telegram_chat_id=6001, is_admin=False)
    db.add(best_pal)
    await db.flush()

    go_getter = GoGetter(
        best_pal_id=best_pal.id,
        name="Charlie",
        display_name="Charlie",
        grade="4",
        telegram_chat_id=6002,
    )
    db.add(go_getter)
    await db.flush()

    target = Target(
        go_getter_id=go_getter.id,
        title="English",
        subject="English",
        description="",
        vacation_type=VacationType.summer,
        vacation_year=date.today().year,
        status=TargetStatus.active,
    )
    db.add(target)
    await db.flush()
    return go_getter, target


@pytest.mark.asyncio
async def test_generate_plan_deactivates_prior_active_plan(db, go_getter_with_target):
    """Generating a second plan must mark the first plan as completed."""
    go_getter, target = go_getter_with_target
    today = date.today()

    # Create an existing active plan manually
    old_plan = Plan(
        target_id=target.id,
        title="Old Plan",
        overview="",
        start_date=today,
        end_date=today + timedelta(days=6),
        total_weeks=1,
        status=PlanStatus.active,
    )
    db.add(old_plan)
    await db.flush()

    assert old_plan.status == PlanStatus.active

    # Patch llm_service so we don't make real API calls
    fake_plan_data = {
        "title": "New Plan",
        "overview": "overview",
        "weeks": [],
    }
    with patch(
        "app.services.plan_generator.llm_service.chat_complete_long",
        new_callable=AsyncMock,
        return_value=(
            __import__("json").dumps(fake_plan_data),
            10,
            20,
        ),
    ):
        from app.services.plan_generator import generate_plan

        new_plan = await generate_plan(
            db=db,
            target=target,
            pupil_name=go_getter.name,
            grade=go_getter.grade,
            start_date=today + timedelta(days=7),
            end_date=today + timedelta(days=13),
            daily_study_minutes=60,
            preferred_days=[0, 1, 2, 3, 4],
        )

    await db.refresh(old_plan)
    assert old_plan.status == PlanStatus.completed, (
        "Prior active plan must be deactivated when a new plan is generated"
    )
    assert new_plan.status == PlanStatus.active


@pytest.mark.asyncio
async def test_only_one_active_plan_after_generate(db, go_getter_with_target):
    """After generation, at most one plan should be active for the go getter."""
    go_getter, target = go_getter_with_target
    today = date.today()

    fake_plan_data = {"title": "P", "overview": "o", "weeks": []}
    with patch(
        "app.services.plan_generator.llm_service.chat_complete_long",
        new_callable=AsyncMock,
        return_value=(__import__("json").dumps(fake_plan_data), 5, 10),
    ):
        from app.services.plan_generator import generate_plan

        await generate_plan(
            db=db,
            target=target,
            pupil_name=go_getter.name,
            grade=go_getter.grade,
            start_date=today,
            end_date=today + timedelta(days=6),
            daily_study_minutes=60,
            preferred_days=[0],
        )
        await generate_plan(
            db=db,
            target=target,
            pupil_name=go_getter.name,
            grade=go_getter.grade,
            start_date=today + timedelta(days=7),
            end_date=today + timedelta(days=13),
            daily_study_minutes=60,
            preferred_days=[0],
        )

    active_plan = await crud_plan.get_active_for_go_getter(db, go_getter.id)
    assert active_plan is not None

    from sqlalchemy import select
    from app.models.target import Target as T

    result = await db.execute(
        select(Plan)
        .join(T, Plan.target_id == T.id)
        .where(T.go_getter_id == go_getter.id, Plan.status == PlanStatus.active)
    )
    active_plans = result.scalars().all()
    assert len(active_plans) == 1, f"Expected 1 active plan, got {len(active_plans)}"
