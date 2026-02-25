from typing import Optional
from pydantic import BaseModel, Field
from app.models.target import VacationType, TargetStatus


class TargetBase(BaseModel):
    title: str = Field(..., max_length=200)
    subject: str = Field(..., max_length=100)
    description: str
    vacation_type: VacationType = VacationType.summer
    vacation_year: int = Field(..., ge=2020, le=2100)
    priority: int = Field(3, ge=1, le=5)


class TargetCreate(TargetBase):
    go_getter_id: int


class TargetUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    subject: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    vacation_type: Optional[VacationType] = None
    vacation_year: Optional[int] = Field(None, ge=2020, le=2100)
    priority: Optional[int] = Field(None, ge=1, le=5)
    status: Optional[TargetStatus] = None


class TargetResponse(TargetBase):
    model_config = {"from_attributes": True}
    id: int
    go_getter_id: int
    status: TargetStatus
