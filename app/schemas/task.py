from typing import Optional
from pydantic import BaseModel, Field
from app.models.task import TaskType


class TaskBase(BaseModel):
    title: str = Field(..., max_length=200)
    description: str
    day_of_week: int = Field(..., ge=0, le=6)
    sequence_in_day: int = Field(1, ge=1)
    estimated_minutes: int = Field(30, ge=5, le=480)
    xp_reward: int = Field(10, ge=1)
    task_type: TaskType = TaskType.practice
    is_optional: bool = False


class TaskResponse(TaskBase):
    model_config = {"from_attributes": True}
    id: int
    milestone_id: int
    checkin_status: Optional[str] = None  # populated dynamically
