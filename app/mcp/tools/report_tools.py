"""Report MCP tools: generate and list reports (role: best_pal/admin for any go_getter; go_getter for own)."""

from datetime import date
from typing import Optional

from app.database import AsyncSessionLocal
from app.mcp.auth import Role, require_role, resolve_role, verify_best_pal_owns_go_getter
from app.mcp.server import mcp
from app.crud import crud_go_getter, crud_report
from app.models.report import ReportType
from app.services import report_service


def _require_chat_id(chat_id: Optional[int]) -> int:
    if chat_id is None:
        raise ValueError("X-Telegram-Chat-Id header is required")
    return chat_id


async def _resolve_go_getter(db, caller_id: int, go_getter_id: Optional[int]):
    """Resolve go_getter_id: best_pals can specify any go_getter, go_getters use their own."""
    role = await resolve_role(db, caller_id)
    if role in (Role.admin, Role.best_pal):
        if go_getter_id is None:
            raise ValueError("go_getter_id is required for best_pal/admin role")
        go_getter = await crud_go_getter.get(db, go_getter_id)
        if not go_getter:
            raise ValueError("Go getter not found")
        await verify_best_pal_owns_go_getter(db, caller_id, go_getter.id)
    else:
        # Go getter uses their own record
        go_getter = await crud_go_getter.get_by_chat_id(db, caller_id)

    if not go_getter:
        raise ValueError("Go getter not found")
    return go_getter


@mcp.tool()
async def generate_daily_report(
    go_getter_id: Optional[int] = None,
    report_date: Optional[str] = None,
    x_telegram_chat_id: Optional[int] = None,
) -> dict:
    """
    Generate a daily progress report. Commits to GitHub.
    Best pal/admin: specify go_getter_id. Go getter: reports on self.
    """
    caller_id = _require_chat_id(x_telegram_chat_id)
    async with AsyncSessionLocal() as db:
        await require_role(db, caller_id, [Role.admin, Role.best_pal, Role.go_getter])
        go_getter = await _resolve_go_getter(db, caller_id, go_getter_id)
        rdate = date.fromisoformat(report_date) if report_date else date.today()
        report = await report_service.generate_daily_report(db, go_getter, rdate)
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
    go_getter_id: Optional[int] = None,
    week_start: Optional[str] = None,
    x_telegram_chat_id: Optional[int] = None,
) -> dict:
    """Generate a weekly progress report. Commits to GitHub."""
    caller_id = _require_chat_id(x_telegram_chat_id)
    async with AsyncSessionLocal() as db:
        await require_role(db, caller_id, [Role.admin, Role.best_pal, Role.go_getter])
        go_getter = await _resolve_go_getter(db, caller_id, go_getter_id)
        ws = date.fromisoformat(week_start) if week_start else None
        report = await report_service.generate_weekly_report(db, go_getter, ws)
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
    go_getter_id: Optional[int] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    x_telegram_chat_id: Optional[int] = None,
) -> dict:
    """Generate a monthly progress report. Commits to GitHub."""
    caller_id = _require_chat_id(x_telegram_chat_id)
    async with AsyncSessionLocal() as db:
        await require_role(db, caller_id, [Role.admin, Role.best_pal, Role.go_getter])
        go_getter = await _resolve_go_getter(db, caller_id, go_getter_id)
        report = await report_service.generate_monthly_report(db, go_getter, year, month)
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
    go_getter_id: Optional[int] = None,
    report_type: Optional[str] = None,
    limit: int = 10,
    x_telegram_chat_id: Optional[int] = None,
) -> list[dict]:
    """List reports for a go getter. Best pal/admin: specify go_getter_id. Go getter: lists own reports."""
    caller_id = _require_chat_id(x_telegram_chat_id)
    async with AsyncSessionLocal() as db:
        await require_role(db, caller_id, [Role.admin, Role.best_pal, Role.go_getter])
        go_getter = await _resolve_go_getter(db, caller_id, go_getter_id)
        rt = ReportType(report_type) if report_type else None
        reports = await crud_report.get_by_go_getter(db, go_getter.id, rt, limit)
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
