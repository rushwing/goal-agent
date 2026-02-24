"""Report MCP tools: generate and list reports (role: parent/admin for any pupil; pupil for own)."""

from datetime import date
from typing import Optional

from app.database import AsyncSessionLocal
from app.mcp.auth import Role, require_role, resolve_role
from app.mcp.server import mcp
from app.crud import crud_pupil, crud_report
from app.models.report import ReportType
from app.services import report_service


def _require_chat_id(chat_id: Optional[int]) -> int:
    if chat_id is None:
        raise ValueError("X-Telegram-Chat-Id header is required")
    return chat_id


async def _resolve_pupil(db, caller_id: int, pupil_id: Optional[int]):
    """Resolve pupil_id: parents can specify any pupil, pupils use their own."""
    from app.models.pupil import Pupil

    role = await resolve_role(db, caller_id)
    if role in (Role.admin, Role.parent):
        if pupil_id is None:
            raise ValueError("pupil_id is required for parent/admin role")
        pupil = await crud_pupil.get(db, pupil_id)
    else:
        # Pupil uses their own record
        pupil = await crud_pupil.get_by_chat_id(db, caller_id)

    if not pupil:
        raise ValueError("Pupil not found")
    return pupil


@mcp.tool()
async def generate_daily_report(
    pupil_id: Optional[int] = None,
    report_date: Optional[str] = None,
    x_telegram_chat_id: Optional[int] = None,
) -> dict:
    """
    Generate a daily progress report. Commits to GitHub.
    Parent/admin: specify pupil_id. Pupil: reports on self.
    """
    caller_id = _require_chat_id(x_telegram_chat_id)
    async with AsyncSessionLocal() as db:
        await require_role(db, caller_id, [Role.admin, Role.parent, Role.pupil])
        pupil = await _resolve_pupil(db, caller_id, pupil_id)
        rdate = date.fromisoformat(report_date) if report_date else date.today()
        report = await report_service.generate_daily_report(db, pupil, rdate)
        await db.commit()
        return {
            "report_id": report.id,
            "period": str(rdate),
            "tasks_completed": report.tasks_completed,
            "tasks_total": report.tasks_total,
            "xp_earned": report.xp_earned,
            "github_file_path": report.github_file_path,
        }


@mcp.tool()
async def generate_weekly_report(
    pupil_id: Optional[int] = None,
    week_start: Optional[str] = None,
    x_telegram_chat_id: Optional[int] = None,
) -> dict:
    """Generate a weekly progress report. Commits to GitHub."""
    caller_id = _require_chat_id(x_telegram_chat_id)
    async with AsyncSessionLocal() as db:
        await require_role(db, caller_id, [Role.admin, Role.parent, Role.pupil])
        pupil = await _resolve_pupil(db, caller_id, pupil_id)
        ws = date.fromisoformat(week_start) if week_start else None
        report = await report_service.generate_weekly_report(db, pupil, ws)
        await db.commit()
        return {
            "report_id": report.id,
            "period_start": str(report.period_start),
            "period_end": str(report.period_end),
            "tasks_completed": report.tasks_completed,
            "tasks_total": report.tasks_total,
            "xp_earned": report.xp_earned,
            "github_file_path": report.github_file_path,
        }


@mcp.tool()
async def generate_monthly_report(
    pupil_id: Optional[int] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    x_telegram_chat_id: Optional[int] = None,
) -> dict:
    """Generate a monthly progress report. Commits to GitHub."""
    caller_id = _require_chat_id(x_telegram_chat_id)
    async with AsyncSessionLocal() as db:
        await require_role(db, caller_id, [Role.admin, Role.parent, Role.pupil])
        pupil = await _resolve_pupil(db, caller_id, pupil_id)
        report = await report_service.generate_monthly_report(db, pupil, year, month)
        await db.commit()
        return {
            "report_id": report.id,
            "period_start": str(report.period_start),
            "period_end": str(report.period_end),
            "tasks_completed": report.tasks_completed,
            "tasks_total": report.tasks_total,
            "xp_earned": report.xp_earned,
            "github_file_path": report.github_file_path,
        }


@mcp.tool()
async def list_reports(
    pupil_id: Optional[int] = None,
    report_type: Optional[str] = None,
    limit: int = 10,
    x_telegram_chat_id: Optional[int] = None,
) -> list[dict]:
    """List reports for a pupil. Parent/admin: specify pupil_id. Pupil: lists own reports."""
    caller_id = _require_chat_id(x_telegram_chat_id)
    async with AsyncSessionLocal() as db:
        await require_role(db, caller_id, [Role.admin, Role.parent, Role.pupil])
        pupil = await _resolve_pupil(db, caller_id, pupil_id)
        rt = ReportType(report_type) if report_type else None
        reports = await crud_report.get_by_pupil(db, pupil.id, rt, limit)
        return [
            {
                "id": r.id,
                "type": r.report_type.value,
                "period_start": str(r.period_start),
                "period_end": str(r.period_end),
                "tasks_completed": r.tasks_completed,
                "tasks_total": r.tasks_total,
                "xp_earned": r.xp_earned,
            }
            for r in reports
        ]
