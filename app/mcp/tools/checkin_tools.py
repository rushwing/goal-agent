"""Check-in MCP tools: task completion, streak, XP (role: go_getter)."""

from datetime import date, timedelta
from typing import Optional

from app.database import AsyncSessionLocal
from app.mcp.auth import Role, require_role
from app.mcp.server import mcp
from app.crud import crud_go_getter, crud_task, crud_check_in, crud_achievement, crud_plan
from app.models.check_in import CheckIn, CheckInStatus
from app.services import streak_service, praise_engine


def _require_chat_id(chat_id: Optional[int]) -> int:
    if chat_id is None:
        raise ValueError("X-Telegram-Chat-Id header is required")
    return chat_id


@mcp.tool()
async def list_today_tasks(
    x_telegram_chat_id: Optional[int] = None,
) -> list[dict]:
    """List today's tasks with check-in status. Requires go_getter role."""
    caller_id = _require_chat_id(x_telegram_chat_id)
    async with AsyncSessionLocal() as db:
        await require_role(db, caller_id, [Role.go_getter])
        go_getter = await crud_go_getter.get_by_chat_id(db, caller_id)
        today = date.today()
        tasks = await crud_task.get_tasks_for_day(db, go_getter.id, today)
        result = []
        for task in tasks:
            ci = await crud_check_in.get_by_task_and_go_getter(db, task.id, go_getter.id)
            result.append(
                {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "estimated_minutes": task.estimated_minutes,
                    "xp_reward": task.xp_reward,
                    "task_type": task.task_type.value,
                    "is_optional": task.is_optional,
                    "status": ci.status.value if ci else "pending",
                }
            )
        return result


@mcp.tool()
async def list_week_tasks(
    x_telegram_chat_id: Optional[int] = None,
) -> list[dict]:
    """List this week's tasks with check-in status. Requires go_getter role."""
    caller_id = _require_chat_id(x_telegram_chat_id)
    async with AsyncSessionLocal() as db:
        await require_role(db, caller_id, [Role.go_getter])
        go_getter = await crud_go_getter.get_by_chat_id(db, caller_id)
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        tasks = await crud_task.get_tasks_for_week(db, go_getter.id, week_start, week_end)
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        result = []
        for task in tasks:
            ci = await crud_check_in.get_by_task_and_go_getter(db, task.id, go_getter.id)
            result.append(
                {
                    "id": task.id,
                    "title": task.title,
                    "day": day_names[task.day_of_week],
                    "estimated_minutes": task.estimated_minutes,
                    "xp_reward": task.xp_reward,
                    "status": ci.status.value if ci else "pending",
                }
            )
        return result


@mcp.tool()
async def checkin_task(
    task_id: int,
    mood_score: int,
    duration_minutes: Optional[int] = None,
    notes: Optional[str] = None,
    x_telegram_chat_id: Optional[int] = None,
) -> dict:
    """
    Check in a completed task. Returns XP earned, streak, and praise message.
    mood_score: 1 (terrible) to 5 (great). Requires go_getter role.
    """
    caller_id = _require_chat_id(x_telegram_chat_id)
    if not 1 <= mood_score <= 5:
        raise ValueError("mood_score must be between 1 and 5")

    async with AsyncSessionLocal() as db:
        await require_role(db, caller_id, [Role.go_getter])
        go_getter = await crud_go_getter.get_by_chat_id(db, caller_id)

        task = await crud_task.get(db, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Idempotent check
        existing = await crud_check_in.get_by_task_and_go_getter(db, task_id, go_getter.id)
        if existing:
            return {
                "already_checked_in": True,
                "check_in_id": existing.id,
                "xp_earned": existing.xp_earned,
                "streak_current": go_getter.streak_current,
                "total_xp": go_getter.xp_total,
                "praise_message": existing.praise_message or "",
                "badges_earned": [],
            }

        # Compute XP & update streak
        xp_result = await streak_service.update_streak_and_xp(
            db=db,
            go_getter=go_getter,
            base_xp=task.xp_reward,
            mood_score=mood_score,
            check_in_date=date.today(),
        )

        # Generate praise
        praise = await praise_engine.generate_praise(
            display_name=go_getter.display_name,
            task_title=task.title,
            mood_score=mood_score,
            streak=xp_result.new_streak,
            grade=go_getter.grade,
            badges_earned=xp_result.badges_earned,
        )

        check_in = CheckIn(
            task_id=task_id,
            go_getter_id=go_getter.id,
            status=CheckInStatus.completed,
            mood_score=mood_score,
            duration_minutes=duration_minutes,
            notes=notes,
            xp_earned=xp_result.xp_earned,
            streak_at_checkin=xp_result.new_streak,
            praise_message=praise,
        )
        db.add(check_in)

        # Update milestone completion count
        from sqlalchemy import select, update
        from app.models.weekly_milestone import WeeklyMilestone

        await db.execute(
            update(WeeklyMilestone)
            .where(WeeklyMilestone.id == task.milestone_id)
            .values(completed_tasks=WeeklyMilestone.completed_tasks + 1)
        )

        await db.commit()

        return {
            "check_in_id": check_in.id,
            "xp_earned": xp_result.xp_earned,
            "streak_current": xp_result.new_streak,
            "total_xp": go_getter.xp_total,
            "praise_message": praise,
            "badges_earned": xp_result.badges_earned,
        }


@mcp.tool()
async def skip_task(
    task_id: int,
    reason: Optional[str] = None,
    x_telegram_chat_id: Optional[int] = None,
) -> dict:
    """Mark a task as skipped. Requires go_getter role."""
    caller_id = _require_chat_id(x_telegram_chat_id)
    async with AsyncSessionLocal() as db:
        await require_role(db, caller_id, [Role.go_getter])
        go_getter = await crud_go_getter.get_by_chat_id(db, caller_id)
        task = await crud_task.get(db, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        existing = await crud_check_in.get_by_task_and_go_getter(db, task_id, go_getter.id)
        if existing:
            return {"already_recorded": True, "status": existing.status.value}

        check_in = CheckIn(
            task_id=task_id,
            go_getter_id=go_getter.id,
            status=CheckInStatus.skipped,
            skip_reason=reason,
            xp_earned=0,
            streak_at_checkin=go_getter.streak_current,
        )
        db.add(check_in)
        await db.commit()
        return {"check_in_id": check_in.id, "status": "skipped", "task_id": task_id}


@mcp.tool()
async def get_go_getter_progress(
    x_telegram_chat_id: Optional[int] = None,
) -> dict:
    """Get go getter's progress summary: streak, XP, active plan, achievements. Requires go_getter role."""
    caller_id = _require_chat_id(x_telegram_chat_id)
    async with AsyncSessionLocal() as db:
        await require_role(db, caller_id, [Role.go_getter])
        go_getter = await crud_go_getter.get_by_chat_id(db, caller_id)
        achievements = await crud_achievement.get_by_go_getter(db, go_getter.id)
        active_plan = await crud_plan.get_active_for_go_getter(db, go_getter.id)

        return {
            "display_name": go_getter.display_name,
            "grade": go_getter.grade,
            "streak_current": go_getter.streak_current,
            "streak_longest": go_getter.streak_longest,
            "xp_total": go_getter.xp_total,
            "active_plan_title": active_plan.title if active_plan else None,
            "recent_achievements": [
                {"badge": a.badge_icon, "name": a.badge_name} for a in achievements[-5:]
            ],
        }
