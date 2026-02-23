"""APScheduler cron jobs (runs in-process with single uvicorn worker)."""
import logging
from datetime import date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _send_daily_tasks():
    """07:30 – send today's task list to each active pupil."""
    from app.crud import crud_pupil, crud_task
    from app.services import telegram_service
    from app.models.notification import RecipientType, NotificationChannel, NotificationType

    async with AsyncSessionLocal() as db:
        pupils = await crud_pupil.get_active(db)
        today = date.today()
        for pupil in pupils:
            tasks = await crud_task.get_tasks_for_day(db, pupil.id, today)
            if not tasks:
                continue
            lines = [f"*Good morning, {pupil.display_name}!* Here are today's study tasks:\n"]
            for i, task in enumerate(tasks, 1):
                opt = " _(optional)_" if task.is_optional else ""
                lines.append(
                    f"{i}. *{task.title}*{opt} — {task.estimated_minutes} min "
                    f"({task.xp_reward} XP)"
                )
            lines.append("\nUse /checkin to mark tasks complete. You've got this! 🌟")
            await telegram_service.send_to_pupil(pupil.telegram_chat_id, "\n".join(lines))


async def _send_evening_reminders():
    """21:00 – remind unchecked tasks and generate daily report."""
    from app.crud import crud_pupil, crud_task, crud_check_in
    from app.services import telegram_service, report_service

    async with AsyncSessionLocal() as db:
        pupils = await crud_pupil.get_active(db)
        today = date.today()
        for pupil in pupils:
            tasks = await crud_task.get_tasks_for_day(db, pupil.id, today)
            unchecked = []
            for task in tasks:
                ci = await crud_check_in.get_by_task_and_pupil(db, task.id, pupil.id)
                if ci is None:
                    unchecked.append(task)

            if unchecked:
                lines = [f"*Hey {pupil.display_name}!* You still have tasks to complete:\n"]
                for task in unchecked:
                    lines.append(f"- {task.title} ({task.estimated_minutes} min)")
                lines.append("\nThere's still time! Check them off to keep your streak alive. 🔥")
                await telegram_service.send_to_pupil(
                    pupil.telegram_chat_id, "\n".join(lines)
                )

            # Generate daily report
            try:
                await report_service.generate_daily_report(db, pupil, today)
                await db.commit()
            except Exception as exc:
                logger.error("Daily report generation failed for %s: %s", pupil.name, exc)
                await db.rollback()


async def _send_weekly_reports():
    """Sunday 20:00 – generate weekly reports and post to Telegram group."""
    from app.crud import crud_pupil
    from app.services import telegram_service, report_service

    async with AsyncSessionLocal() as db:
        pupils = await crud_pupil.get_active(db)
        today = date.today()
        week_start = today - timedelta(days=today.weekday())

        for pupil in pupils:
            try:
                report = await report_service.generate_weekly_report(db, pupil, week_start)
                await db.commit()
                # Send summary to group
                summary = (
                    f"*Weekly Report – {pupil.display_name}*\n\n"
                    f"Tasks: {report.tasks_completed}/{report.tasks_total} completed\n"
                    f"XP earned: {report.xp_earned}\n\n"
                    f"Full report committed to GitHub ✅"
                )
                await telegram_service.send_to_group(summary)
            except Exception as exc:
                logger.error("Weekly report failed for %s: %s", pupil.name, exc)
                await db.rollback()


async def _send_monthly_reports():
    """1st of month 08:00 – generate monthly reports."""
    from app.crud import crud_pupil
    from app.services import telegram_service, report_service

    async with AsyncSessionLocal() as db:
        pupils = await crud_pupil.get_active(db)
        today = date.today()
        # Report for previous month
        first_of_month = date(today.year, today.month, 1)
        prev_month_end = first_of_month - timedelta(days=1)

        for pupil in pupils:
            try:
                report = await report_service.generate_monthly_report(
                    db, pupil, prev_month_end.year, prev_month_end.month
                )
                await db.commit()
                summary = (
                    f"*Monthly Report – {pupil.display_name}*\n\n"
                    f"Tasks: {report.tasks_completed}/{report.tasks_total} completed\n"
                    f"XP earned: {report.xp_earned}\n\n"
                    f"Full report committed to GitHub ✅"
                )
                await telegram_service.send_to_group(summary)
            except Exception as exc:
                logger.error("Monthly report failed for %s: %s", pupil.name, exc)
                await db.rollback()


def setup_scheduler():
    """Register all cron jobs. Call once at app startup."""
    scheduler.add_job(
        _send_daily_tasks,
        CronTrigger(hour=7, minute=30),
        id="daily_tasks",
        replace_existing=True,
    )
    scheduler.add_job(
        _send_evening_reminders,
        CronTrigger(hour=21, minute=0),
        id="evening_reminders",
        replace_existing=True,
    )
    scheduler.add_job(
        _send_weekly_reports,
        CronTrigger(day_of_week="sun", hour=20, minute=0),
        id="weekly_reports",
        replace_existing=True,
    )
    scheduler.add_job(
        _send_monthly_reports,
        CronTrigger(day=1, hour=8, minute=0),
        id="monthly_reports",
        replace_existing=True,
    )
    logger.info("Scheduler jobs registered: %s", [j.id for j in scheduler.get_jobs()])
