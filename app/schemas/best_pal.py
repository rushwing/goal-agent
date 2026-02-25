from typing import Optional
from pydantic import BaseModel, Field


class BestPalBase(BaseModel):
    name: str = Field(..., max_length=100)
    telegram_chat_id: int
    is_admin: bool = False


class BestPalCreate(BestPalBase):
    pass


class BestPalUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    telegram_chat_id: Optional[int] = None
    is_admin: Optional[bool] = None


class BestPalResponse(BestPalBase):
    model_config = {"from_attributes": True}
    id: int
