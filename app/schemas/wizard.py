"""Pydantic schemas for the GoalGroup creation wizard."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.goal_group_wizard import WizardStatus


class WizardCreate(BaseModel):
    go_getter_id: int


class ScopeRequest(BaseModel):
    title: str
    description: Optional[str] = None
    start_date: date
    end_date: date


class TargetSpec(BaseModel):
    target_id: int
    subcategory_id: int
    priority: int = Field(default=3, ge=1, le=5)


class TargetsRequest(BaseModel):
    target_specs: list[TargetSpec]


class ConstraintSpec(BaseModel):
    daily_minutes: int = Field(default=60, ge=1)
    preferred_days: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4, 5, 6])


class ConstraintsRequest(BaseModel):
    # Key is subcategory_id (int); Pydantic coerces int keys from JSON strings
    constraints: dict[int, ConstraintSpec]


class AdjustRequest(BaseModel):
    target_specs: Optional[list[TargetSpec]] = None
    constraints: Optional[dict[int, ConstraintSpec]] = None


class FeasibilityRiskOut(BaseModel):
    rule_code: str
    level: str
    subcategory_id: Optional[int]
    detail: str
    llm_explanation: str
    is_blocker: bool


class WizardResponse(BaseModel):
    id: int
    go_getter_id: int
    status: WizardStatus
    group_title: Optional[str]
    group_description: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    target_specs: Optional[list[Any]]
    constraints: Optional[dict[str, Any]]
    draft_plan_ids: Optional[list[Any]]
    feasibility_passed: Optional[bool]
    feasibility_risks: list[FeasibilityRiskOut]
    goal_group_id: Optional[int]
    generation_errors: Optional[list[Any]]
    expires_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
