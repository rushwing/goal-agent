"""Plan and target endpoints."""
from datetime import date
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.v1.deps import require_parent_or_admin, require_admin
from app.crud import crud_target, crud_plan, crud_pupil
from app.schemas.target import TargetCreate, TargetUpdate, TargetResponse
from app.schemas.plan import PlanUpdate, PlanResponse, GeneratePlanRequest
from app.services import plan_generator, github_service
from app.models.plan import Plan
from app.models.weekly_milestone import WeeklyMilestone
from app.models.target import VacationType

router = APIRouter(tags=["plans"])


@router.get("/targets", response_model=list[TargetResponse])
async def list_targets(
    pupil_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[int, Depends(require_parent_or_admin)],
):
    return await crud_target.get_by_pupil(db, pupil_id)


@router.post("/targets", response_model=TargetResponse, status_code=201)
async def create_target(
    body: TargetCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[int, Depends(require_parent_or_admin)],
):
    return await crud_target.create(db, obj_in=body)


@router.patch("/targets/{target_id}", response_model=TargetResponse)
async def update_target(
    target_id: int,
    body: TargetUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[int, Depends(require_parent_or_admin)],
):
    target = await crud_target.get(db, target_id)
    if not target:
        raise HTTPException(404, "Target not found")
    return await crud_target.update(db, db_obj=target, obj_in=body)


@router.delete("/targets/{target_id}")
async def delete_target(
    target_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[int, Depends(require_admin)],
):
    t = await crud_target.remove(db, id=target_id)
    if not t:
        raise HTTPException(404, "Target not found")
    return {"success": True}


@router.get("/plans", response_model=list[PlanResponse])
async def list_plans(
    pupil_id: Optional[int] = None,
    target_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _: int = Depends(require_parent_or_admin),
):
    if pupil_id:
        return await crud_plan.get_by_pupil(db, pupil_id, target_id)
    return await crud_plan.get_multi(db)


@router.post("/plans/generate", status_code=201)
async def generate_plan(
    body: GeneratePlanRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[int, Depends(require_parent_or_admin)],
):
    target = await crud_target.get(db, body.target_id)
    if not target:
        raise HTTPException(404, "Target not found")
    pupil = await crud_pupil.get(db, target.pupil_id)
    if not pupil:
        raise HTTPException(404, "Pupil not found")

    plan = await plan_generator.generate_plan(
        db=db,
        target=target,
        pupil_name=pupil.name,
        grade=pupil.grade,
        start_date=body.start_date,
        end_date=body.end_date,
        daily_study_minutes=body.daily_study_minutes,
        preferred_days=body.preferred_days,
        extra_instructions=body.extra_instructions,
    )

    from app.mcp.tools.plan_tools import _plan_to_markdown

    full_plan = (await db.execute(
        select(Plan)
        .options(selectinload(Plan.milestones).selectinload(WeeklyMilestone.tasks))
        .where(Plan.id == plan.id)
    )).scalar_one()

    md = _plan_to_markdown(full_plan, pupil.name, target)
    try:
        sha, path = await github_service.commit_plan(
            pupil.name, target.vacation_type.value, target.vacation_year, plan.title, md
        )
        plan.github_commit_sha = sha
        plan.github_file_path = path
        await db.flush()
    except Exception:
        pass

    return {
        "plan_id": plan.id,
        "title": plan.title,
        "start_date": str(plan.start_date),
        "end_date": str(plan.end_date),
        "total_weeks": plan.total_weeks,
        "status": plan.status.value,
    }


@router.patch("/plans/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: int,
    body: PlanUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[int, Depends(require_parent_or_admin)],
):
    plan = await crud_plan.get(db, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    return await crud_plan.update(db, db_obj=plan, obj_in=body)


@router.delete("/plans/{plan_id}")
async def delete_plan(
    plan_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[int, Depends(require_admin)],
):
    p = await crud_plan.remove(db, id=plan_id)
    if not p:
        raise HTTPException(404, "Plan not found")
    return {"success": True}
