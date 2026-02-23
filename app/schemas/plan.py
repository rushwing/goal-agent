from datetime import date
from typing import Optional
from pydantic import BaseModel, Field
from app.models.plan import PlanStatus


class PlanBase(BaseModel):
    title: str = Field(..., max_length=200)
    overview: str
    start_date: date
    end_date: date
    total_weeks: int = Field(..., ge=1)


class PlanCreate(PlanBase):
    target_id: int


class PlanUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    overview: Optional[str] = None
    status: Optional[PlanStatus] = None


class PlanResponse(PlanBase):
    model_config = {"from_attributes": True}
    id: int
    target_id: int
    status: PlanStatus
    github_commit_sha: Optional[str]
    github_file_path: Optional[str]
    llm_prompt_tokens: int
    llm_completion_tokens: int


class GeneratePlanRequest(BaseModel):
    target_id: int
    start_date: date
    end_date: date
    daily_study_minutes: int = Field(60, ge=15, le=480)
    preferred_days: list[int] = Field(default=[0, 1, 2, 3, 4], description="0=Mon..6=Sun")
    extra_instructions: Optional[str] = None
