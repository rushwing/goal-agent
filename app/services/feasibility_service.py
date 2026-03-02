"""Feasibility rule engine + optional LLM explanation enrichment for the wizard."""

import json
import logging
from dataclasses import dataclass, field
from typing import Literal, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.goal_group_wizard import GoalGroupWizard

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rule codes (module-level constants)
# ---------------------------------------------------------------------------

RULE_SPAN_TOO_SHORT = "RULE_SPAN_TOO_SHORT"
RULE_DUPLICATE_SUBCATEGORY = "RULE_DUPLICATE_SUBCATEGORY"
RULE_EXISTING_ACTIVE_SUBCATEGORY = "RULE_EXISTING_ACTIVE_SUBCATEGORY"
RULE_EXISTING_ACTIVE_GROUP = "RULE_EXISTING_ACTIVE_GROUP"
RULE_OVERLOAD = "RULE_OVERLOAD"
RULE_SINGLE_TARGET_OVERLOAD = "RULE_SINGLE_TARGET_OVERLOAD"
RULE_TOO_FEW_DAYS = "RULE_TOO_FEW_DAYS"

# Grade-based total daily minutes limit
_DAILY_MINUTES_LIMIT = 120


# ---------------------------------------------------------------------------
# Risk dataclass
# ---------------------------------------------------------------------------


@dataclass
class FeasibilityRisk:
    rule_code: str
    level: Literal["error", "warning", "info"]
    subcategory_id: Optional[int]
    detail: str
    llm_explanation: str = field(default="")
    is_blocker: bool = field(default=False)

    def __post_init__(self) -> None:
        # Errors are always blockers
        if self.level == "error":
            self.is_blocker = True

    def to_dict(self) -> dict:
        return {
            "rule_code": self.rule_code,
            "level": self.level,
            "subcategory_id": self.subcategory_id,
            "detail": self.detail,
            "llm_explanation": self.llm_explanation,
            "is_blocker": self.is_blocker,
        }


# ---------------------------------------------------------------------------
# Rule helpers
# ---------------------------------------------------------------------------


def _get_constraints_for_subcategory(
    wizard_constraints: Optional[dict], subcategory_id: int
) -> dict:
    """Look up constraints dict by subcategory_id (handles string or int JSON keys)."""
    if not wizard_constraints:
        return {}
    # JSON keys are always strings, but we accept both
    return (
        wizard_constraints.get(str(subcategory_id)) or wizard_constraints.get(subcategory_id) or {}
    )


# ---------------------------------------------------------------------------
# Main check
# ---------------------------------------------------------------------------


async def check_feasibility(
    db: AsyncSession,
    wizard: GoalGroupWizard,
) -> list[FeasibilityRisk]:
    """Run all feasibility rules against the wizard state.

    Returns a list of FeasibilityRisk objects (may be empty = all clear).
    """
    from app.models.goal_group import GoalGroup, GoalGroupStatus
    from app.models.plan import Plan, PlanStatus
    from app.models.target import Target, TargetStatus

    risks: list[FeasibilityRisk] = []

    # ── RULE_SPAN_TOO_SHORT ────────────────────────────────────────────────
    if wizard.start_date and wizard.end_date:
        span = (wizard.end_date - wizard.start_date).days
        if span < 7:
            risks.append(
                FeasibilityRisk(
                    rule_code=RULE_SPAN_TOO_SHORT,
                    level="error",
                    subcategory_id=None,
                    detail=f"Plan span is {span} days — minimum 7 days required.",
                )
            )

    target_specs = wizard.target_specs or []

    # ── RULE_DUPLICATE_SUBCATEGORY ─────────────────────────────────────────
    seen_subcategories: set[int] = set()
    for spec in target_specs:
        sub_id = spec.get("subcategory_id")
        if sub_id is None:
            continue
        if sub_id in seen_subcategories:
            risks.append(
                FeasibilityRisk(
                    rule_code=RULE_DUPLICATE_SUBCATEGORY,
                    level="error",
                    subcategory_id=sub_id,
                    detail=f"Subcategory {sub_id} appears more than once in target specs.",
                )
            )
        seen_subcategories.add(sub_id)

    # ── RULE_EXISTING_ACTIVE_SUBCATEGORY ───────────────────────────────────
    for spec in target_specs:
        sub_id = spec.get("subcategory_id")
        target_id = spec.get("target_id")
        if sub_id is None:
            continue
        result = await db.execute(
            select(Plan)
            .join(Target, Plan.target_id == Target.id)
            .where(
                Target.go_getter_id == wizard.go_getter_id,
                Target.subcategory_id == sub_id,
                Target.status == TargetStatus.active,
                Plan.status == PlanStatus.active,
                Target.id != target_id,  # exclude the wizard's own target
            )
        )
        conflicting_plan = result.scalar_one_or_none()
        if conflicting_plan is not None:
            risks.append(
                FeasibilityRisk(
                    rule_code=RULE_EXISTING_ACTIVE_SUBCATEGORY,
                    level="error",
                    subcategory_id=sub_id,
                    detail=(
                        f"Subcategory {sub_id} already has active Plan #{conflicting_plan.id} "
                        f"('{conflicting_plan.title}'). This wizard cannot confirm while that "
                        "plan is active — it belongs to a different target and will NOT be "
                        "automatically replaced. Cancel or complete that plan first, then retry."
                    ),
                )
            )

    # ── RULE_EXISTING_ACTIVE_GROUP ─────────────────────────────────────────
    result = await db.execute(
        select(GoalGroup).where(
            GoalGroup.go_getter_id == wizard.go_getter_id,
            GoalGroup.status == GoalGroupStatus.active,
        )
    )
    if result.scalar_one_or_none() is not None:
        risks.append(
            FeasibilityRisk(
                rule_code=RULE_EXISTING_ACTIVE_GROUP,
                level="warning",
                subcategory_id=None,
                detail=(
                    "This go_getter already has an active GoalGroup. "
                    "Confirming the wizard will attempt to create another one."
                ),
            )
        )

    # ── Constraint-based rules ─────────────────────────────────────────────
    wizard_constraints = wizard.constraints or {}
    total_daily_minutes = 0

    for spec in target_specs:
        sub_id = spec.get("subcategory_id")
        constraint = _get_constraints_for_subcategory(wizard_constraints, sub_id) if sub_id else {}
        daily_minutes = constraint.get("daily_minutes", 60)
        preferred_days = constraint.get("preferred_days", [0, 1, 2, 3, 4, 5, 6])

        total_daily_minutes += daily_minutes

        # ── RULE_SINGLE_TARGET_OVERLOAD ────────────────────────────────────
        if daily_minutes > _DAILY_MINUTES_LIMIT:
            risks.append(
                FeasibilityRisk(
                    rule_code=RULE_SINGLE_TARGET_OVERLOAD,
                    level="warning",
                    subcategory_id=sub_id,
                    detail=(
                        f"Target with subcategory {sub_id} has {daily_minutes} daily minutes, "
                        f"which exceeds the recommended {_DAILY_MINUTES_LIMIT} minutes."
                    ),
                )
            )

        # ── RULE_TOO_FEW_DAYS ──────────────────────────────────────────────
        if len(preferred_days) < 3:
            risks.append(
                FeasibilityRisk(
                    rule_code=RULE_TOO_FEW_DAYS,
                    level="warning",
                    subcategory_id=sub_id,
                    detail=(
                        f"Target with subcategory {sub_id} has only {len(preferred_days)} "
                        "preferred study day(s) — at least 3 recommended for consistency."
                    ),
                )
            )

    # ── RULE_OVERLOAD ──────────────────────────────────────────────────────
    if total_daily_minutes > _DAILY_MINUTES_LIMIT and len(target_specs) > 1:
        risks.append(
            FeasibilityRisk(
                rule_code=RULE_OVERLOAD,
                level="warning",
                subcategory_id=None,
                detail=(
                    f"Total daily study time across all targets is {total_daily_minutes} minutes, "
                    f"which exceeds the recommended {_DAILY_MINUTES_LIMIT} minutes."
                ),
            )
        )

    return risks


# ---------------------------------------------------------------------------
# LLM enrichment
# ---------------------------------------------------------------------------


async def enrich_with_llm(risks: list[FeasibilityRisk]) -> list[FeasibilityRisk]:
    """Fill llm_explanation on each risk via a single LLM call.

    If the LLM call fails, returns risks unchanged (best-effort enrichment).
    """
    if not risks:
        return risks

    from app.services import llm_service

    prompt_items = [{"rule_code": r.rule_code, "level": r.level, "detail": r.detail} for r in risks]
    system_prompt = (
        "You are an educational planning advisor helping a parent or teacher "
        "understand feasibility issues with a study plan. "
        "For each issue listed, write one friendly sentence (max 30 words) explaining "
        "the problem and suggesting how to fix it. "
        "Return ONLY a JSON array of strings, one per issue, in the same order. "
        "No markdown, no extra text."
    )
    user_prompt = json.dumps(prompt_items, ensure_ascii=False)

    try:
        content, _, _ = await llm_service.chat_complete(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=512,
        )
        explanations = json.loads(content)
        if isinstance(explanations, list) and len(explanations) == len(risks):
            for risk, explanation in zip(risks, explanations, strict=False):
                risk.llm_explanation = str(explanation)
    except Exception as exc:
        logger.warning("LLM feasibility enrichment failed: %s", exc)

    return risks
