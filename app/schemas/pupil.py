from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


class PupilBase(BaseModel):
    name: str = Field(..., max_length=100)
    display_name: str = Field(..., max_length=50)
    grade: str = Field(..., max_length=20)
    telegram_chat_id: int


class PupilCreate(PupilBase):
    parent_id: Optional[int] = None


class PupilUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    display_name: Optional[str] = Field(None, max_length=50)
    grade: Optional[str] = Field(None, max_length=20)
    telegram_chat_id: Optional[int] = None
    is_active: Optional[bool] = None


class PupilResponse(PupilBase):
    model_config = {"from_attributes": True}

    id: int
    xp_total: int
    streak_current: int
    streak_longest: int
    streak_last_date: Optional[date]
    is_active: bool
