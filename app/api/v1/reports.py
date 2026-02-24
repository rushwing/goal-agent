"""Report endpoints."""

from datetime import date
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.v1.deps import require_any_role
from app.mcp.auth import resolve_role, Role
from app.crud import crud_pupil, crud_report
from app.crud.parents import crud_parent
from app.models.report import ReportType
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])


async def _resolve_pupil(db, chat_id: int, pupil_id: Optional[int]):
    role = await resolve_role(db, chat_id)
    if role in (Role.admin, Role.parent):
        if pupil_id is None:
            raise HTTPException(400, "pupil_id required")
        pupil = await crud_pupil.get(db, pupil_id)
        if not pupil:
            raise HTTPException(404, "Pupil not found")
        if role == Role.parent:
            parent = await crud_parent.get_by_chat_id(db, chat_id)
            if not parent or pupil.parent_id != parent.id:
                raise HTTPException(403, "Not authorized to access this pupil")
    else:
        pupil = await crud_pupil.get_by_chat_id(db, chat_id)
        if not pupil:
            raise HTTPException(404, "Pupil not found")
    return pupil


@router.get("")
async def list_reports(
    pupil_id: Optional[int] = None,
    report_type: Optional[str] = None,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    chat_id: int = Depends(require_any_role),
):
    pupil = await _resolve_pupil(db, chat_id, pupil_id)
    rt = ReportType(report_type) if report_type else None
    return await crud_report.get_by_pupil(db, pupil.id, rt, limit)


@router.post("/daily", status_code=201)
async def create_daily_report(
    pupil_id: Optional[int] = None,
    report_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    chat_id: int = Depends(require_any_role),
):
    pupil = await _resolve_pupil(db, chat_id, pupil_id)
    report = await report_service.generate_daily_report(db, pupil, report_date)
    return {"report_id": report.id, "xp_earned": report.xp_earned}


@router.post("/weekly", status_code=201)
async def create_weekly_report(
    pupil_id: Optional[int] = None,
    week_start: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    chat_id: int = Depends(require_any_role),
):
    pupil = await _resolve_pupil(db, chat_id, pupil_id)
    report = await report_service.generate_weekly_report(db, pupil, week_start)
    return {"report_id": report.id, "xp_earned": report.xp_earned}


@router.post("/monthly", status_code=201)
async def create_monthly_report(
    pupil_id: Optional[int] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    chat_id: int = Depends(require_any_role),
):
    pupil = await _resolve_pupil(db, chat_id, pupil_id)
    report = await report_service.generate_monthly_report(db, pupil, year, month)
    return {"report_id": report.id, "xp_earned": report.xp_earned}
