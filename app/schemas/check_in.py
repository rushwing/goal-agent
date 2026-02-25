from typing import Optional
from pydantic import BaseModel, Field
from app.models.check_in import CheckInStatus


class CheckInCreate(BaseModel):
    task_id: int
    mood_score: int = Field(..., ge=1, le=5)
    duration_minutes: Optional[int] = Field(None, ge=1)
    notes: Optional[str] = None


class SkipTaskRequest(BaseModel):
    task_id: int
    reason: Optional[str] = None


class CheckInResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    task_id: int
    go_getter_id: int
    status: CheckInStatus
    mood_score: Optional[int]
    duration_minutes: Optional[int]
    notes: Optional[str]
    xp_earned: int
    streak_at_checkin: int
    praise_message: Optional[str]
    skip_reason: Optional[str]


class CheckInResult(BaseModel):
    check_in: CheckInResponse
    xp_earned: int
    streak_current: int
    total_xp: int
    praise_message: str
    badges_earned: list[str] = []
