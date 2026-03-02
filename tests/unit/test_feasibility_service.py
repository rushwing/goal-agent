"""Unit tests for the feasibility rule engine."""

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.feasibility_service import (
    RULE_DUPLICATE_SUBCATEGORY,
    RULE_EXISTING_ACTIVE_GROUP,
    RULE_EXISTING_ACTIVE_SUBCATEGORY,
    RULE_OVERLOAD,
    RULE_SINGLE_TARGET_OVERLOAD,
    RULE_SPAN_TOO_SHORT,
    RULE_TOO_FEW_DAYS,
    FeasibilityRisk,
    check_feasibility,
    enrich_with_llm,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_wizard(
    start_date=None,
    end_date=None,
    target_specs=None,
    constraints=None,
    go_getter_id=1,
):
    return SimpleNamespace(
        go_getter_id=go_getter_id,
        start_date=start_date,
        end_date=end_date,
        target_specs=target_specs or [],
        constraints=constraints or {},
    )


def _mock_db_no_conflicts():
    """DB that returns no active plans and no active groups."""
    db = AsyncMock()
    empty_result = MagicMock()
    empty_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=empty_result)
    return db


# ---------------------------------------------------------------------------
# RULE_SPAN_TOO_SHORT
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rule_span_too_short_fires():
    today = date.today()
    wizard = _make_wizard(start_date=today, end_date=today + timedelta(days=5))
    db = _mock_db_no_conflicts()
    risks = await check_feasibility(db, wizard)
    codes = [r.rule_code for r in risks]
    assert RULE_SPAN_TOO_SHORT in codes
    blocker = next(r for r in risks if r.rule_code == RULE_SPAN_TOO_SHORT)
    assert blocker.is_blocker is True


@pytest.mark.asyncio
async def test_rule_span_too_short_does_not_fire_at_exactly_7():
    today = date.today()
    wizard = _make_wizard(start_date=today, end_date=today + timedelta(days=7))
    db = _mock_db_no_conflicts()
    risks = await check_feasibility(db, wizard)
    codes = [r.rule_code for r in risks]
    assert RULE_SPAN_TOO_SHORT not in codes


# ---------------------------------------------------------------------------
# RULE_DUPLICATE_SUBCATEGORY
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rule_duplicate_subcategory_fires():
    today = date.today()
    wizard = _make_wizard(
        start_date=today,
        end_date=today + timedelta(days=14),
        target_specs=[
            {"target_id": 1, "subcategory_id": 5, "priority": 3},
            {"target_id": 2, "subcategory_id": 5, "priority": 3},
        ],
    )
    db = _mock_db_no_conflicts()
    risks = await check_feasibility(db, wizard)
    codes = [r.rule_code for r in risks]
    assert RULE_DUPLICATE_SUBCATEGORY in codes
    dup = next(r for r in risks if r.rule_code == RULE_DUPLICATE_SUBCATEGORY)
    assert dup.is_blocker is True
    assert dup.subcategory_id == 5


@pytest.mark.asyncio
async def test_rule_duplicate_subcategory_does_not_fire_for_different_subcategories():
    today = date.today()
    wizard = _make_wizard(
        start_date=today,
        end_date=today + timedelta(days=14),
        target_specs=[
            {"target_id": 1, "subcategory_id": 1, "priority": 3},
            {"target_id": 2, "subcategory_id": 2, "priority": 3},
        ],
    )
    db = _mock_db_no_conflicts()
    risks = await check_feasibility(db, wizard)
    codes = [r.rule_code for r in risks]
    assert RULE_DUPLICATE_SUBCATEGORY not in codes


# ---------------------------------------------------------------------------
# RULE_EXISTING_ACTIVE_SUBCATEGORY
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rule_existing_active_subcategory_fires():
    from unittest.mock import call

    today = date.today()
    wizard = _make_wizard(
        start_date=today,
        end_date=today + timedelta(days=14),
        target_specs=[{"target_id": 1, "subcategory_id": 3, "priority": 3}],
    )

    db = AsyncMock()
    # First call: RULE_EXISTING_ACTIVE_SUBCATEGORY check — returns a plan
    conflict_result = MagicMock()
    mock_conflicting_plan = MagicMock()
    mock_conflicting_plan.id = 99
    mock_conflicting_plan.title = "Existing Math Plan"
    conflict_result.scalar_one_or_none.return_value = mock_conflicting_plan
    # Second call: RULE_EXISTING_ACTIVE_GROUP check — no active group
    empty_result = MagicMock()
    empty_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(side_effect=[conflict_result, empty_result])

    risks = await check_feasibility(db, wizard)
    codes = [r.rule_code for r in risks]
    assert RULE_EXISTING_ACTIVE_SUBCATEGORY in codes
    risk = next(r for r in risks if r.rule_code == RULE_EXISTING_ACTIVE_SUBCATEGORY)
    assert risk.is_blocker is True
    assert risk.subcategory_id == 3


# ---------------------------------------------------------------------------
# RULE_EXISTING_ACTIVE_GROUP
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rule_existing_active_group_fires():
    today = date.today()
    wizard = _make_wizard(
        start_date=today,
        end_date=today + timedelta(days=14),
        target_specs=[{"target_id": 1, "subcategory_id": 1, "priority": 3}],
    )

    db = AsyncMock()
    # RULE_EXISTING_ACTIVE_SUBCATEGORY: no conflict
    empty_result = MagicMock()
    empty_result.scalar_one_or_none.return_value = None
    # RULE_EXISTING_ACTIVE_GROUP: active group found
    group_result = MagicMock()
    group_result.scalar_one_or_none.return_value = object()
    db.execute = AsyncMock(side_effect=[empty_result, group_result])

    risks = await check_feasibility(db, wizard)
    codes = [r.rule_code for r in risks]
    assert RULE_EXISTING_ACTIVE_GROUP in codes
    risk = next(r for r in risks if r.rule_code == RULE_EXISTING_ACTIVE_GROUP)
    assert risk.level == "warning"
    assert risk.is_blocker is False


# ---------------------------------------------------------------------------
# RULE_OVERLOAD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rule_overload_fires_when_total_exceeds_limit():
    today = date.today()
    wizard = _make_wizard(
        start_date=today,
        end_date=today + timedelta(days=14),
        target_specs=[
            {"target_id": 1, "subcategory_id": 1, "priority": 3},
            {"target_id": 2, "subcategory_id": 2, "priority": 3},
        ],
        constraints={
            "1": {"daily_minutes": 90, "preferred_days": [0, 1, 2, 3, 4]},
            "2": {"daily_minutes": 90, "preferred_days": [0, 1, 2, 3, 4]},
        },
    )
    db = _mock_db_no_conflicts()
    risks = await check_feasibility(db, wizard)
    codes = [r.rule_code for r in risks]
    assert RULE_OVERLOAD in codes
    risk = next(r for r in risks if r.rule_code == RULE_OVERLOAD)
    assert risk.level == "warning"
    assert risk.is_blocker is False


@pytest.mark.asyncio
async def test_rule_overload_does_not_fire_for_single_target():
    """Single target overloaded should fire RULE_SINGLE_TARGET_OVERLOAD, not RULE_OVERLOAD."""
    today = date.today()
    wizard = _make_wizard(
        start_date=today,
        end_date=today + timedelta(days=14),
        target_specs=[{"target_id": 1, "subcategory_id": 1, "priority": 3}],
        constraints={"1": {"daily_minutes": 150, "preferred_days": [0, 1, 2, 3, 4]}},
    )
    db = _mock_db_no_conflicts()
    risks = await check_feasibility(db, wizard)
    codes = [r.rule_code for r in risks]
    assert RULE_OVERLOAD not in codes
    assert RULE_SINGLE_TARGET_OVERLOAD in codes


# ---------------------------------------------------------------------------
# RULE_SINGLE_TARGET_OVERLOAD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rule_single_target_overload_fires():
    today = date.today()
    wizard = _make_wizard(
        start_date=today,
        end_date=today + timedelta(days=14),
        target_specs=[{"target_id": 1, "subcategory_id": 1, "priority": 3}],
        constraints={"1": {"daily_minutes": 180, "preferred_days": [0, 1, 2, 3, 4]}},
    )
    db = _mock_db_no_conflicts()
    risks = await check_feasibility(db, wizard)
    codes = [r.rule_code for r in risks]
    assert RULE_SINGLE_TARGET_OVERLOAD in codes
    risk = next(r for r in risks if r.rule_code == RULE_SINGLE_TARGET_OVERLOAD)
    assert risk.subcategory_id == 1


# ---------------------------------------------------------------------------
# RULE_TOO_FEW_DAYS
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rule_too_few_days_fires():
    today = date.today()
    wizard = _make_wizard(
        start_date=today,
        end_date=today + timedelta(days=14),
        target_specs=[{"target_id": 1, "subcategory_id": 1, "priority": 3}],
        constraints={"1": {"daily_minutes": 60, "preferred_days": [0, 1]}},
    )
    db = _mock_db_no_conflicts()
    risks = await check_feasibility(db, wizard)
    codes = [r.rule_code for r in risks]
    assert RULE_TOO_FEW_DAYS in codes
    risk = next(r for r in risks if r.rule_code == RULE_TOO_FEW_DAYS)
    assert risk.level == "warning"
    assert risk.is_blocker is False


@pytest.mark.asyncio
async def test_rule_too_few_days_does_not_fire_at_3():
    today = date.today()
    wizard = _make_wizard(
        start_date=today,
        end_date=today + timedelta(days=14),
        target_specs=[{"target_id": 1, "subcategory_id": 1, "priority": 3}],
        constraints={"1": {"daily_minutes": 60, "preferred_days": [0, 1, 2]}},
    )
    db = _mock_db_no_conflicts()
    risks = await check_feasibility(db, wizard)
    codes = [r.rule_code for r in risks]
    assert RULE_TOO_FEW_DAYS not in codes


# ---------------------------------------------------------------------------
# No risks for clean wizard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_risks_for_clean_wizard():
    today = date.today()
    wizard = _make_wizard(
        start_date=today,
        end_date=today + timedelta(days=30),
        target_specs=[
            {"target_id": 1, "subcategory_id": 1, "priority": 3},
            {"target_id": 2, "subcategory_id": 2, "priority": 2},
        ],
        constraints={
            "1": {"daily_minutes": 45, "preferred_days": [0, 1, 2, 3, 4]},
            "2": {"daily_minutes": 45, "preferred_days": [0, 1, 2, 3, 4]},
        },
    )
    db = _mock_db_no_conflicts()
    risks = await check_feasibility(db, wizard)
    assert risks == []


# ---------------------------------------------------------------------------
# FeasibilityRisk.is_blocker auto-set
# ---------------------------------------------------------------------------


def test_error_level_risk_is_always_blocker():
    risk = FeasibilityRisk(
        rule_code=RULE_SPAN_TOO_SHORT,
        level="error",
        subcategory_id=None,
        detail="too short",
    )
    assert risk.is_blocker is True


def test_warning_level_risk_is_not_blocker():
    risk = FeasibilityRisk(
        rule_code=RULE_TOO_FEW_DAYS,
        level="warning",
        subcategory_id=1,
        detail="few days",
    )
    assert risk.is_blocker is False


# ---------------------------------------------------------------------------
# enrich_with_llm
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enrich_with_llm_fills_explanations():
    import json

    risks = [
        FeasibilityRisk(
            rule_code=RULE_SPAN_TOO_SHORT,
            level="error",
            subcategory_id=None,
            detail="too short",
        ),
        FeasibilityRisk(
            rule_code=RULE_TOO_FEW_DAYS,
            level="warning",
            subcategory_id=1,
            detail="few days",
        ),
    ]
    explanations = ["First explanation.", "Second explanation."]
    with patch(
        "app.services.llm_service.chat_complete",
        new_callable=AsyncMock,
        return_value=(json.dumps(explanations), 10, 20),
    ):
        enriched = await enrich_with_llm(risks)

    assert enriched[0].llm_explanation == "First explanation."
    assert enriched[1].llm_explanation == "Second explanation."


@pytest.mark.asyncio
async def test_enrich_with_llm_returns_unchanged_on_error():
    risks = [
        FeasibilityRisk(
            rule_code=RULE_SPAN_TOO_SHORT,
            level="error",
            subcategory_id=None,
            detail="too short",
        )
    ]
    with patch(
        "app.services.llm_service.chat_complete",
        new_callable=AsyncMock,
        side_effect=RuntimeError("LLM unavailable"),
    ):
        enriched = await enrich_with_llm(risks)

    assert enriched[0].llm_explanation == ""


@pytest.mark.asyncio
async def test_enrich_with_llm_empty_input_returns_empty():
    enriched = await enrich_with_llm([])
    assert enriched == []
