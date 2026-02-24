"""Generate daily/weekly/monthly Markdown reports using LLM."""

import logging
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.check_in import CheckIn, CheckInStatus
from app.models.pupil import Pupil
from app.models.report import Report, ReportType
from app.services import llm_service, github_service
from app.crud.reports import crud_report

logger = logging.getLogger(__name__)


async def _fetch_check_ins(
    db: AsyncSession, pupil_id: int, start: date, end: date
) -> list[CheckIn]:
    """Fetch check-ins by actual event date (created_at), not milestone coverage."""
    result = await db.execute(
        select(CheckIn).where(
            CheckIn.pupil_id == pupil_id,
            func.date(CheckIn.created_at) >= start,
            func.date(CheckIn.created_at) <= end,
        )
    )
    return list(result.scalars().all())


def _build_stats(check_ins: list[CheckIn]) -> dict:
    total = len(check_ins)
    completed = sum(1 for c in check_ins if c.status == CheckInStatus.completed)
    skipped = sum(1 for c in check_ins if c.status == CheckInStatus.skipped)
    xp = sum(c.xp_earned for c in check_ins if c.status == CheckInStatus.completed)
    return {"total": total, "completed": completed, "skipped": skipped, "xp": xp}


REPORT_SYSTEM = (
    "You are a friendly, encouraging study coach writing a progress report for a family. "
    "Write in Markdown. Be positive but honest. Highlight achievements and suggest improvements. "
    "Keep the report concise and parent-friendly."
)


async def _generate_content(
    pupil_name: str,
    grade: str,
    report_type: str,
    period_label: str,
    stats: dict,
    check_ins: list[CheckIn],
) -> str:
    task_lines = "\n".join(
        f"- {c.status.value}: Task ID {c.task_id} (XP: {c.xp_earned}, mood: {c.mood_score})"
        for c in check_ins[:30]  # cap context
    )
    user_prompt = (
        f"Student: {pupil_name} (Grade {grade})\n"
        f"Report type: {report_type}\n"
        f"Period: {period_label}\n\n"
        f"Statistics:\n"
        f"- Total tasks: {stats['total']}\n"
        f"- Completed: {stats['completed']}\n"
        f"- Skipped: {stats['skipped']}\n"
        f"- XP earned: {stats['xp']}\n\n"
        f"Task details (sample):\n{task_lines}\n\n"
        f"Write a {report_type} progress report."
    )
    try:
        content, _, _ = await llm_service.chat_complete(
            messages=[
                {"role": "system", "content": REPORT_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.5,
            max_tokens=1500,
        )
        return content.strip()
    except Exception as exc:
        logger.warning("LLM report generation failed, using fallback: %s", exc)
        return _fallback_report(pupil_name, report_type, period_label, stats)


def _fallback_report(pupil_name: str, report_type: str, period_label: str, stats: dict) -> str:
    completion_pct = round(stats["completed"] / stats["total"] * 100) if stats["total"] > 0 else 0
    return (
        f"# {report_type.capitalize()} Report – {pupil_name}\n\n"
        f"**Period:** {period_label}\n\n"
        f"## Summary\n\n"
        f"- **Tasks completed:** {stats['completed']} / {stats['total']} ({completion_pct}%)\n"
        f"- **Tasks skipped:** {stats['skipped']}\n"
        f"- **XP earned:** {stats['xp']}\n"
    )


async def generate_daily_report(
    db: AsyncSession, pupil: Pupil, report_date: Optional[date] = None
) -> Report:
    report_date = report_date or date.today()
    existing = await crud_report.get_existing(db, pupil.id, ReportType.daily, report_date)
    if existing:
        logger.info(
            "Daily report for pupil %d on %s already exists (id=%d), reusing",
            pupil.id,
            report_date,
            existing.id,
        )
        return existing
    check_ins = await _fetch_check_ins(db, pupil.id, report_date, report_date)
    stats = _build_stats(check_ins)
    period_label = str(report_date)
    content = await _generate_content(
        pupil.name, pupil.grade, "daily", period_label, stats, check_ins
    )

    report = Report(
        pupil_id=pupil.id,
        report_type=ReportType.daily,
        period_start=report_date,
        period_end=report_date,
        content_md=content,
        tasks_total=stats["total"],
        tasks_completed=stats["completed"],
        tasks_skipped=stats["skipped"],
        xp_earned=stats["xp"],
    )
    db.add(report)
    await db.flush()

    try:
        sha, path = await github_service.commit_report(
            pupil.name, "daily", report_date.year, period_label, content
        )
        report.github_commit_sha = sha
        report.github_file_path = path
    except Exception as exc:
        logger.warning("GitHub commit for daily report failed: %s", exc)

    await db.flush()
    return report


async def generate_weekly_report(
    db: AsyncSession, pupil: Pupil, week_start: Optional[date] = None
) -> Report:
    if week_start is None:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    existing = await crud_report.get_existing(db, pupil.id, ReportType.weekly, week_start)
    if existing:
        logger.info(
            "Weekly report for pupil %d week_start=%s already exists (id=%d), reusing",
            pupil.id,
            week_start,
            existing.id,
        )
        return existing
    check_ins = await _fetch_check_ins(db, pupil.id, week_start, week_end)
    stats = _build_stats(check_ins)
    period_label = f"week_{week_start.isocalendar().week:02d}_{week_start.year}"
    content = await _generate_content(
        pupil.name, pupil.grade, "weekly", f"{week_start} to {week_end}", stats, check_ins
    )

    report = Report(
        pupil_id=pupil.id,
        report_type=ReportType.weekly,
        period_start=week_start,
        period_end=week_end,
        content_md=content,
        tasks_total=stats["total"],
        tasks_completed=stats["completed"],
        tasks_skipped=stats["skipped"],
        xp_earned=stats["xp"],
    )
    db.add(report)
    await db.flush()

    try:
        sha, path = await github_service.commit_report(
            pupil.name, "weekly", week_start.year, period_label, content
        )
        report.github_commit_sha = sha
        report.github_file_path = path
    except Exception as exc:
        logger.warning("GitHub commit for weekly report failed: %s", exc)

    await db.flush()
    return report


async def generate_monthly_report(
    db: AsyncSession, pupil: Pupil, year: Optional[int] = None, month: Optional[int] = None
) -> Report:
    today = date.today()
    year = year or today.year
    month = month or today.month
    period_start = date(year, month, 1)
    # Last day of month
    if month == 12:
        period_end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        period_end = date(year, month + 1, 1) - timedelta(days=1)

    existing = await crud_report.get_existing(db, pupil.id, ReportType.monthly, period_start)
    if existing:
        logger.info(
            "Monthly report for pupil %d %d-%02d already exists (id=%d), reusing",
            pupil.id,
            year,
            month,
            existing.id,
        )
        return existing
    check_ins = await _fetch_check_ins(db, pupil.id, period_start, period_end)
    stats = _build_stats(check_ins)
    period_label = f"{year}_{month:02d}"
    content = await _generate_content(
        pupil.name, pupil.grade, "monthly", f"{year}-{month:02d}", stats, check_ins
    )

    report = Report(
        pupil_id=pupil.id,
        report_type=ReportType.monthly,
        period_start=period_start,
        period_end=period_end,
        content_md=content,
        tasks_total=stats["total"],
        tasks_completed=stats["completed"],
        tasks_skipped=stats["skipped"],
        xp_earned=stats["xp"],
    )
    db.add(report)
    await db.flush()

    try:
        sha, path = await github_service.commit_report(
            pupil.name, "monthly", year, period_label, content
        )
        report.github_commit_sha = sha
        report.github_file_path = path
    except Exception as exc:
        logger.warning("GitHub commit for monthly report failed: %s", exc)

    await db.flush()
    return report
