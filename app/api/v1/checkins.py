"""Check-in endpoints for go_getters."""

from datetime import date
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.v1.deps import require_any_role, get_chat_id
from app.mcp.auth import resolve_role, Role
from app.crud import crud_go_getter, crud_task, crud_check_in
from app.schemas.check_in import CheckInCreate, SkipTaskRequest, CheckInResult
from app.models.check_in import CheckIn, CheckInStatus
from app.services import streak_service, praise_engine

router = APIRouter(prefix="/checkins", tags=["checkins"])


@router.get("/today")
async def get_today_tasks(
    db: Annotated[AsyncSession, Depends(get_db)],
    chat_id: Annotated[int, Depends(require_any_role)],
):
    role = await resolve_role(db, chat_id)
    if role != Role.go_getter:
        raise HTTPException(403, "Go getter role required")
    go_getter = await crud_go_getter.get_by_chat_id(db, chat_id)
    from app.crud.tasks import crud_task

    tasks = await crud_task.get_tasks_for_day(db, go_getter.id, date.today())
    result = []
    for task in tasks:
        ci = await crud_check_in.get_by_task_and_go_getter(db, task.id, go_getter.id)
        result.append(
            {
                "id": task.id,
                "title": task.title,
                "estimated_minutes": task.estimated_minutes,
                "xp_reward": task.xp_reward,
                "is_optional": task.is_optional,
                "status": ci.status.value if ci else "pending",
            }
        )
    return result


@router.post("", status_code=201)
async def checkin_task(
    body: CheckInCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    chat_id: Annotated[int, Depends(require_any_role)],
):
    role = await resolve_role(db, chat_id)
    if role != Role.go_getter:
        raise HTTPException(403, "Go getter role required")
    go_getter = await crud_go_getter.get_by_chat_id(db, chat_id)
    task = await crud_task.get(db, body.task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    if not await crud_task.get_with_ownership(db, body.task_id, go_getter.id):
        raise HTTPException(403, "Task does not belong to this go getter")
    if not await crud_task.get_eligible_for_date(db, body.task_id, go_getter.id, date.today()):
        raise HTTPException(422, "Task is not scheduled for today")

    existing = await crud_check_in.get_by_task_and_go_getter(db, body.task_id, go_getter.id)
    if existing:
        return {"already_checked_in": True}

    xp_result = await streak_service.update_streak_and_xp(
        db=db,
        go_getter=go_getter,
        base_xp=task.xp_reward,
        mood_score=body.mood_score,
        check_in_date=date.today(),
    )
    praise = await praise_engine.generate_praise(
        display_name=go_getter.display_name,
        task_title=task.title,
        mood_score=body.mood_score,
        streak=xp_result.new_streak,
        grade=go_getter.grade,
        badges_earned=xp_result.badges_earned,
    )
    ci = CheckIn(
        task_id=body.task_id,
        go_getter_id=go_getter.id,
        status=CheckInStatus.completed,
        mood_score=body.mood_score,
        duration_minutes=body.duration_minutes,
        notes=body.notes,
        xp_earned=xp_result.xp_earned,
        streak_at_checkin=xp_result.new_streak,
        praise_message=praise,
    )
    db.add(ci)
    await db.flush()
    return {
        "check_in_id": ci.id,
        "xp_earned": xp_result.xp_earned,
        "streak_current": xp_result.new_streak,
        "total_xp": go_getter.xp_total,
        "praise_message": praise,
        "badges_earned": xp_result.badges_earned,
    }


@router.post("/skip", status_code=201)
async def skip_task(
    body: SkipTaskRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    chat_id: Annotated[int, Depends(require_any_role)],
):
    role = await resolve_role(db, chat_id)
    if role != Role.go_getter:
        raise HTTPException(403, "Go getter role required")
    go_getter = await crud_go_getter.get_by_chat_id(db, chat_id)
    task = await crud_task.get(db, body.task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    if not await crud_task.get_with_ownership(db, body.task_id, go_getter.id):
        raise HTTPException(403, "Task does not belong to this go getter")
    if not await crud_task.get_eligible_for_date(db, body.task_id, go_getter.id, date.today()):
        raise HTTPException(422, "Task is not scheduled for today")
    existing = await crud_check_in.get_by_task_and_go_getter(db, body.task_id, go_getter.id)
    if existing:
        return {"already_recorded": True}
    ci = CheckIn(
        task_id=body.task_id,
        go_getter_id=go_getter.id,
        status=CheckInStatus.skipped,
        skip_reason=body.reason,
        xp_earned=0,
        streak_at_checkin=go_getter.streak_current,
    )
    db.add(ci)
    await db.flush()
    return {"check_in_id": ci.id, "status": "skipped"}
