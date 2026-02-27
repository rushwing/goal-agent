"""Track taxonomy endpoints (read-only for clients)."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_any_role
from app.crud.tracks import get_all_categories, get_subcategories
from app.database import get_db

router = APIRouter(prefix="/tracks", tags=["tracks"])


class SubcategoryResponse(BaseModel):
    id: int
    category_id: int
    name: str
    description: Optional[str]
    sort_order: int

    model_config = {"from_attributes": True}


class CategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    icon: Optional[str]
    color: Optional[str]
    sort_order: int
    subcategories: list[SubcategoryResponse] = []

    model_config = {"from_attributes": True}


@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[int, Depends(require_any_role)],
):
    """Return all active track categories with their subcategories."""
    return await get_all_categories(db)


@router.get("/subcategories", response_model=list[SubcategoryResponse])
async def list_subcategories(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[int, Depends(require_any_role)],
    category_id: Optional[int] = None,
):
    """Return subcategories, optionally filtered by category."""
    return await get_subcategories(db, category_id=category_id)
