"""Report endpoints."""

from datetime import date
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.v1.deps import require_any_role
from app.mcp.auth import resolve_role, Role
from app.crud import crud_go_getter, crud_report
from app.crud.best_pals import crud_best_pal
from app.models.report import ReportType
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])


async def _resolve_go_getter(db, chat_id: int, go_getter_id: Optional[int]):
    role = await resolve_role(db, chat_id)
    if role in (Role.admin, Role.best_pal):
        if go_getter_id is None:
            raise HTTPException(400, "go_getter_id required")
        go_getter = await crud_go_getter.get(db, go_getter_id)
        if not go_getter:
            raise HTTPException(404, "Go getter not found")
        if role == Role.best_pal:
            best_pal = await crud_best_pal.get_by_chat_id(db, chat_id)
            if not best_pal or go_getter.best_pal_id != best_pal.id:
                raise HTTPException(403, "Not authorized to access this go getter")
    else:
        go_getter = await crud_go_getter.get_by_chat_id(db, chat_id)
        if not go_getter:
            raise HTTPException(404, "Go getter not found")
    return go_getter


@router.get("")
async def list_reports(
    go_getter_id: Optional[int] = None,
    report_type: Optional[str] = None,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    chat_id: int = Depends(require_any_role),
):
    go_getter = await _resolve_go_getter(db, chat_id, go_getter_id)
    rt = ReportType(report_type) if report_type else None
    return await crud_report.get_by_go_getter(db, go_getter.id, rt, limit)


@router.post("/daily", status_code=201)
async def create_daily_report(
    go_getter_id: Optional[int] = None,
    report_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    chat_id: int = Depends(require_any_role),
):
    go_getter = await _resolve_go_getter(db, chat_id, go_getter_id)
    report = await report_service.generate_daily_report(db, go_getter, report_date)
    return {"report_id": report.id, "xp_earned": report.xp_earned}


@router.post("/weekly", status_code=201)
async def create_weekly_report(
    go_getter_id: Optional[int] = None,
    week_start: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    chat_id: int = Depends(require_any_role),
):
    go_getter = await _resolve_go_getter(db, chat_id, go_getter_id)
    report = await report_service.generate_weekly_report(db, go_getter, week_start)
    return {"report_id": report.id, "xp_earned": report.xp_earned}


@router.post("/monthly", status_code=201)
async def create_monthly_report(
    go_getter_id: Optional[int] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    chat_id: int = Depends(require_any_role),
):
    go_getter = await _resolve_go_getter(db, chat_id, go_getter_id)
    report = await report_service.generate_monthly_report(db, go_getter, year, month)
    return {"report_id": report.id, "xp_earned": report.xp_earned}
