from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


class GoGetterBase(BaseModel):
    name: str = Field(..., max_length=100)
    display_name: str = Field(..., max_length=50)
    grade: str = Field(..., max_length=20)
    telegram_chat_id: int


class GoGetterCreate(GoGetterBase):
    best_pal_id: Optional[int] = None


class GoGetterUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    display_name: Optional[str] = Field(None, max_length=50)
    grade: Optional[str] = Field(None, max_length=20)
    telegram_chat_id: Optional[int] = None
    is_active: Optional[bool] = None


class GoGetterResponse(GoGetterBase):
    model_config = {"from_attributes": True}

    id: int
    best_pal_id: Optional[int]
    xp_total: int
    streak_current: int
    streak_longest: int
    streak_last_date: Optional[date]
    is_active: bool
