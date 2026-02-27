"""GoalGroup endpoints: create groups, add/remove targets, trigger re-planning."""

from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_best_pal_or_admin, verify_best_pal_owns_go_getter
from app.crud.goal_groups import create as crud_create_group, get as crud_get_group
from app.crud.targets import crud_target
from app.database import get_db
from app.models.goal_group import GoalGroupStatus
from app.models.target import TargetStatus
from app.services.goal_group_service import add_target_to_group, remove_target_from_group

router = APIRouter(prefix="/goal-groups", tags=["goal-groups"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class GoalGroupCreate(BaseModel):
    go_getter_id: int
    title: str
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class GoalGroupResponse(BaseModel):
    id: int
    go_getter_id: int
    title: str
    description: Optional[str]
    status: GoalGroupStatus
    start_date: Optional[date]
    end_date: Optional[date]

    model_config = {"from_attributes": True}


class AddTargetRequest(BaseModel):
    target_id: int


class ChangeResponse(BaseModel):
    change_id: int
    message: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("", response_model=GoalGroupResponse, status_code=201)
async def create_goal_group(
    body: GoalGroupCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    chat_id: Annotated[int, Depends(require_best_pal_or_admin)],
):
    """Create a new GoalGroup (time-bounded planning window) for a GoGetter."""
    await verify_best_pal_owns_go_getter(body.go_getter_id, chat_id, db)
    group = await crud_create_group(
        db,
        go_getter_id=body.go_getter_id,
        title=body.title,
        description=body.description,
        start_date=body.start_date,
        end_date=body.end_date,
    )
    return group


@router.get("/{group_id}", response_model=GoalGroupResponse)
async def get_goal_group(
    group_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    chat_id: Annotated[int, Depends(require_best_pal_or_admin)],
):
    group = await crud_get_group(db, group_id)
    if not group:
        raise HTTPException(404, "GoalGroup not found")
    await verify_best_pal_owns_go_getter(group.go_getter_id, chat_id, db)
    return group


@router.post("/{group_id}/targets", response_model=ChangeResponse, status_code=201)
async def add_target(
    group_id: int,
    body: AddTargetRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    chat_id: Annotated[int, Depends(require_best_pal_or_admin)],
):
    """Add an existing Target to a GoalGroup.

    Enforces the 7-day change cooldown and subcategory uniqueness constraint.
    Triggers asynchronous re-planning for the group.
    """
    group = await crud_get_group(db, group_id)
    if not group:
        raise HTTPException(404, "GoalGroup not found")
    if group.status != GoalGroupStatus.active:
        raise HTTPException(409, "GoalGroup is not active")
    await verify_best_pal_owns_go_getter(group.go_getter_id, chat_id, db)

    target = await crud_target.get(db, body.target_id)
    if not target:
        raise HTTPException(404, "Target not found")
    if target.go_getter_id != group.go_getter_id:
        raise HTTPException(403, "Target does not belong to this GoGetter")
    if target.status == TargetStatus.cancelled:
        raise HTTPException(409, "Cannot add a cancelled target")

    try:
        change = await add_target_to_group(db, group=group, target=target)
    except ValueError as e:
        raise HTTPException(409, str(e)) from e

    return ChangeResponse(change_id=change.id, message="Target added and re-planning triggered.")


@router.delete("/{group_id}/targets/{target_id}", response_model=ChangeResponse)
async def remove_target(
    group_id: int,
    target_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    chat_id: Annotated[int, Depends(require_best_pal_or_admin)],
):
    """Remove (cancel) a Target from a GoalGroup.

    Enforces the 7-day change cooldown. Supersedes future tasks and triggers
    re-planning for remaining targets in the group.
    """
    group = await crud_get_group(db, group_id)
    if not group:
        raise HTTPException(404, "GoalGroup not found")
    if group.status != GoalGroupStatus.active:
        raise HTTPException(409, "GoalGroup is not active")
    await verify_best_pal_owns_go_getter(group.go_getter_id, chat_id, db)

    target = await crud_target.get(db, target_id)
    if not target:
        raise HTTPException(404, "Target not found")
    if target.group_id != group_id:
        raise HTTPException(409, "Target is not in this GoalGroup")
    if target.status == TargetStatus.cancelled:
        raise HTTPException(409, "Target is already cancelled")

    try:
        change = await remove_target_from_group(db, group=group, target=target)
    except ValueError as e:
        raise HTTPException(409, str(e)) from e

    return ChangeResponse(change_id=change.id, message="Target removed and re-planning triggered.")
