"""Unit tests for wizard_service state transitions and confirm logic."""

from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from app.models.best_pal import BestPal
from app.models.go_getter import GoGetter
from app.models.goal_group_wizard import GoalGroupWizard, WizardStatus
from app.models.target import Target, VacationType, TargetStatus
from app.services import wizard_service


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def go_getter(db):
    bp = BestPal(name="Parent", telegram_chat_id=7001, is_admin=False)
    db.add(bp)
    await db.flush()

    gg = GoGetter(
        best_pal_id=bp.id,
        name="Alex",
        display_name="Alex",
        grade="5",
        telegram_chat_id=7002,
    )
    db.add(gg)
    await db.flush()
    return gg


@pytest_asyncio.fixture
async def target(db, go_getter):
    t = Target(
        go_getter_id=go_getter.id,
        title="Math Practice",
        subject="Math",
        description="Daily math drills",
        vacation_type=VacationType.summer,
        vacation_year=date.today().year,
        subcategory_id=1,
        status=TargetStatus.active,
    )
    db.add(t)
    await db.flush()
    return t


@pytest_asyncio.fixture
async def wizard(db, go_getter):
    wiz = await wizard_service.create_wizard(db, go_getter_id=go_getter.id)
    return wiz


# ---------------------------------------------------------------------------
# create_wizard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_wizard_initial_state(db, go_getter):
    wiz = await wizard_service.create_wizard(db, go_getter_id=go_getter.id)
    assert wiz.status == WizardStatus.collecting_scope
    assert wiz.go_getter_id == go_getter.id
    assert wiz.expires_at is not None


@pytest.mark.asyncio
async def test_create_wizard_blocks_duplicate(db, go_getter, wizard):
    with pytest.raises(ValueError, match="active wizard"):
        await wizard_service.create_wizard(db, go_getter_id=go_getter.id)


# ---------------------------------------------------------------------------
# set_scope
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_scope_transitions_to_collecting_targets(db, wizard):
    today = date.today()
    updated = await wizard_service.set_scope(
        db,
        wizard,
        title="Summer Goals",
        description="Study hard",
        start_date=today,
        end_date=today + timedelta(days=30),
    )
    assert updated.status == WizardStatus.collecting_targets
    assert updated.group_title == "Summer Goals"
    assert updated.start_date == today


@pytest.mark.asyncio
async def test_set_scope_rejects_short_span(db, wizard):
    today = date.today()
    with pytest.raises(ValueError, match="7 days"):
        await wizard_service.set_scope(
            db,
            wizard,
            title="T",
            description=None,
            start_date=today,
            end_date=today + timedelta(days=5),
        )


# ---------------------------------------------------------------------------
# set_targets
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_targets_transitions_to_collecting_constraints(db, wizard, target):
    today = date.today()
    # First set scope
    await wizard_service.set_scope(
        db,
        wizard,
        title="S",
        description=None,
        start_date=today,
        end_date=today + timedelta(days=30),
    )
    updated = await wizard_service.set_targets(
        db,
        wizard,
        target_specs=[
            {"target_id": target.id, "subcategory_id": target.subcategory_id, "priority": 3}
        ],
    )
    assert updated.status == WizardStatus.collecting_constraints
    assert len(updated.target_specs) == 1


@pytest.mark.asyncio
async def test_set_targets_rejects_wrong_go_getter(db, go_getter, wizard):
    # Create another go_getter and target
    other_bp = BestPal(name="Other", telegram_chat_id=8001, is_admin=False)
    db.add(other_bp)
    await db.flush()
    other_gg = GoGetter(
        best_pal_id=other_bp.id,
        name="Other",
        display_name="Other",
        grade="3",
        telegram_chat_id=8002,
    )
    db.add(other_gg)
    await db.flush()
    other_target = Target(
        go_getter_id=other_gg.id,
        title="Other Target",
        subject="Science",
        description="",
        vacation_type=VacationType.summer,
        vacation_year=date.today().year,
        status=TargetStatus.active,
    )
    db.add(other_target)
    await db.flush()

    with pytest.raises(ValueError, match="does not belong"):
        await wizard_service.set_targets(
            db,
            wizard,
            target_specs=[{"target_id": other_target.id, "subcategory_id": 1, "priority": 3}],
        )


# ---------------------------------------------------------------------------
# cancel_wizard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_wizard_transitions_to_cancelled(db, wizard):
    await wizard_service.cancel_wizard(db, wizard)
    assert wizard.status == WizardStatus.cancelled


@pytest.mark.asyncio
async def test_cancel_wizard_idempotent_on_terminal(db, wizard):
    await wizard_service.cancel_wizard(db, wizard)
    # Second cancel should be a no-op
    await wizard_service.cancel_wizard(db, wizard)
    assert wizard.status == WizardStatus.cancelled


# ---------------------------------------------------------------------------
# assert_not_terminal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_scope_raises_on_terminal_wizard(db, go_getter):
    wiz = await wizard_service.create_wizard(db, go_getter_id=go_getter.id)
    await wizard_service.cancel_wizard(db, wiz)
    with pytest.raises(ValueError, match="terminal state"):
        await wizard_service.set_scope(
            db,
            wiz,
            title="T",
            description=None,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=10),
        )


# ---------------------------------------------------------------------------
# set_constraints + happy path through feasibility_check
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_constraints_triggers_generation_and_feasibility(db, wizard, target, go_getter):
    today = date.today()
    # Set scope
    await wizard_service.set_scope(
        db,
        wizard,
        title="Summer Plan",
        description=None,
        start_date=today,
        end_date=today + timedelta(days=30),
    )
    # Set targets
    await wizard_service.set_targets(
        db,
        wizard,
        target_specs=[{"target_id": target.id, "subcategory_id": 1, "priority": 3}],
    )

    fake_plan_data = {"title": "Math Plan", "overview": "overview", "weeks": []}

    with (
        patch(
            "app.services.plan_generator.llm_service.chat_complete_long",
            new_callable=AsyncMock,
            return_value=(__import__("json").dumps(fake_plan_data), 10, 20),
        ),
        patch(
            "app.services.llm_service.chat_complete",
            new_callable=AsyncMock,
            return_value=(__import__("json").dumps(["looks good"]), 5, 10),
        ),
    ):
        updated = await wizard_service.set_constraints(
            db,
            wizard,
            constraints={1: {"daily_minutes": 45, "preferred_days": [0, 1, 2, 3, 4]}},
        )

    assert updated.status == WizardStatus.feasibility_check
    assert updated.draft_plan_ids is not None
    assert len(updated.draft_plan_ids) == 1
    assert updated.feasibility_passed is not None


# ---------------------------------------------------------------------------
# confirm happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confirm_creates_goal_group(db, wizard, target, go_getter):
    today = date.today()
    await wizard_service.set_scope(
        db,
        wizard,
        title="Summer Plan",
        description="Desc",
        start_date=today,
        end_date=today + timedelta(days=30),
    )
    await wizard_service.set_targets(
        db,
        wizard,
        target_specs=[{"target_id": target.id, "subcategory_id": 1, "priority": 3}],
    )

    fake_plan_data = {"title": "Math Plan", "overview": "overview", "weeks": []}

    with (
        patch(
            "app.services.plan_generator.llm_service.chat_complete_long",
            new_callable=AsyncMock,
            return_value=(__import__("json").dumps(fake_plan_data), 10, 20),
        ),
        patch(
            "app.services.llm_service.chat_complete",
            new_callable=AsyncMock,
            return_value=(__import__("json").dumps([""]), 5, 10),
        ),
    ):
        await wizard_service.set_constraints(
            db,
            wizard,
            constraints={1: {"daily_minutes": 45, "preferred_days": [0, 1, 2, 3, 4]}},
        )

    # feasibility_passed should be 1 (no blockers in clean scenario)
    assert wizard.feasibility_passed == 1

    group = await wizard_service.confirm(db, wizard)
    assert group.id is not None
    assert group.go_getter_id == go_getter.id
    assert group.title == "Summer Plan"
    assert wizard.status == WizardStatus.confirmed
    assert wizard.goal_group_id == group.id


# ---------------------------------------------------------------------------
# confirm blocked by feasibility
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confirm_raises_when_feasibility_failed(db, wizard):
    # Manually set feasibility_passed = 0
    from app.crud.wizards import update_wizard

    await update_wizard(db, wizard, feasibility_passed=0)
    with pytest.raises(ValueError, match="blocking feasibility issues"):
        await wizard_service.confirm(db, wizard)


# ---------------------------------------------------------------------------
# P0: draft generation must not deactivate live plans
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_draft_generation_does_not_deactivate_existing_active_plan(
    db, wizard, target, go_getter
):
    """Entering /constraints must leave any pre-existing active plan untouched."""
    from app.models.plan import Plan, PlanStatus

    today = date.today()

    # Create an existing active plan for the target
    live_plan = Plan(
        target_id=target.id,
        title="Live Plan",
        overview="",
        start_date=today,
        end_date=today + timedelta(days=30),
        total_weeks=4,
        status=PlanStatus.active,
    )
    db.add(live_plan)
    await db.flush()

    await wizard_service.set_scope(
        db,
        wizard,
        title="T",
        description=None,
        start_date=today,
        end_date=today + timedelta(days=30),
    )
    await wizard_service.set_targets(
        db,
        wizard,
        target_specs=[
            {"target_id": target.id, "subcategory_id": target.subcategory_id, "priority": 3}
        ],
    )

    fake_plan_data = {"title": "Draft Plan", "overview": "", "weeks": []}
    with (
        patch(
            "app.services.plan_generator.llm_service.chat_complete_long",
            new_callable=AsyncMock,
            return_value=(__import__("json").dumps(fake_plan_data), 10, 20),
        ),
        patch(
            "app.services.llm_service.chat_complete",
            new_callable=AsyncMock,
            return_value=(__import__("json").dumps([""]), 5, 10),
        ),
    ):
        await wizard_service.set_constraints(
            db,
            wizard,
            constraints={1: {"daily_minutes": 45, "preferred_days": [0, 1, 2, 3, 4]}},
        )

    await db.refresh(live_plan)
    assert live_plan.status == PlanStatus.active, (
        "Existing active plan must not be completed during draft generation"
    )


@pytest.mark.asyncio
async def test_confirm_deactivates_existing_active_plan(db, wizard, target, go_getter):
    """confirm() must complete the pre-existing active plan when activating the draft."""
    from app.models.plan import Plan, PlanStatus

    today = date.today()

    live_plan = Plan(
        target_id=target.id,
        title="Live Plan",
        overview="",
        start_date=today,
        end_date=today + timedelta(days=30),
        total_weeks=4,
        status=PlanStatus.active,
    )
    db.add(live_plan)
    await db.flush()

    await wizard_service.set_scope(
        db,
        wizard,
        title="T",
        description=None,
        start_date=today,
        end_date=today + timedelta(days=30),
    )
    await wizard_service.set_targets(
        db,
        wizard,
        target_specs=[
            {"target_id": target.id, "subcategory_id": target.subcategory_id, "priority": 3}
        ],
    )

    fake_plan_data = {"title": "Draft Plan", "overview": "", "weeks": []}
    with (
        patch(
            "app.services.plan_generator.llm_service.chat_complete_long",
            new_callable=AsyncMock,
            return_value=(__import__("json").dumps(fake_plan_data), 10, 20),
        ),
        patch(
            "app.services.llm_service.chat_complete",
            new_callable=AsyncMock,
            return_value=(__import__("json").dumps([""]), 5, 10),
        ),
    ):
        await wizard_service.set_constraints(
            db,
            wizard,
            constraints={1: {"daily_minutes": 45, "preferred_days": [0, 1, 2, 3, 4]}},
        )

    assert wizard.feasibility_passed == 1
    await wizard_service.confirm(db, wizard)

    await db.refresh(live_plan)
    assert live_plan.status == PlanStatus.completed, (
        "Pre-existing active plan must be completed when the draft is activated on confirm"
    )


# ---------------------------------------------------------------------------
# P1: confirm must be blocked when generation_errors is non-empty
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confirm_raises_when_generation_errors(db, wizard):
    from app.crud.wizards import update_wizard

    await update_wizard(
        db,
        wizard,
        feasibility_passed=1,
        draft_plan_ids=[999],  # non-empty so the generation_errors guard is reached
        generation_errors=[{"target_id": 5, "error": "LLM timeout"}],
    )
    with pytest.raises(ValueError, match="generation failed"):
        await wizard_service.confirm(db, wizard)


# ---------------------------------------------------------------------------
# P1: set_targets must normalize subcategory_id from DB, not client input
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_targets_normalizes_subcategory_id(db, wizard, target, go_getter):
    """Client-supplied subcategory_id must be overridden by the DB value."""
    today = date.today()
    await wizard_service.set_scope(
        db,
        wizard,
        title="T",
        description=None,
        start_date=today,
        end_date=today + timedelta(days=30),
    )

    # target.subcategory_id == 1; client sends 99 (wrong)
    updated = await wizard_service.set_targets(
        db,
        wizard,
        target_specs=[{"target_id": target.id, "subcategory_id": 99, "priority": 3}],
    )

    stored = updated.target_specs[0]
    assert stored["subcategory_id"] == target.subcategory_id, (
        "subcategory_id in stored spec must reflect DB value, not client-supplied value"
    )
