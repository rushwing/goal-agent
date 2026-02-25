"""Polling-based Telegram go getter bot (Issue #8).

Go getters can interact with their goal agent directly from Telegram without
needing the OpenClaw plugin.  Auth relies on Telegram-guaranteed
`update.effective_user.id` — no spoofable header is involved.

Handlers
--------
/start               – welcome message and usage hints
/today               – today's tasks with inline Done / Skip buttons
/checkin <id>        – check in a task (default mood 3)
/skip <id> [reason]  – skip a task with optional reason
callback done:<id>   – inline button → same as /checkin <id>
callback skip:<id>   – inline button → same as /skip <id>

Graceful degradation: start_go_getter_bot() is only called from main.py when
TELEGRAM_GO_GETTER_BOT_TOKEN is non-empty, so this module is never imported in
environments where the token is absent.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.config import get_settings
from app.crud import crud_check_in, crud_go_getter, crud_task
from app.database import AsyncSessionLocal
from app.models.check_in import CheckIn, CheckInStatus
from app.models.go_getter import GoGetter
from app.services import praise_engine, streak_service

logger = logging.getLogger(__name__)
settings = get_settings()


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------


async def _get_go_getter_or_reply(update: Update, db) -> Optional[GoGetter]:
    """Resolve the Telegram user to a registered go getter, or reply with an error."""
    chat_id = update.effective_user.id  # type: ignore[union-attr]
    go_getter = await crud_go_getter.get_by_chat_id(db, chat_id)
    if not go_getter:
        await update.message.reply_text(  # type: ignore[union-attr]
            "You are not registered. Contact your best pal."
        )
        return None
    return go_getter


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(  # type: ignore[union-attr]
        "Hi! I'm your Goal Agent bot.\n\n"
        "Commands:\n"
        "  /today — show today's tasks\n"
        "  /checkin <id> — mark a task done\n"
        "  /skip <id> [reason] — skip a task\n"
    )


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with AsyncSessionLocal() as db:
        go_getter = await _get_go_getter_or_reply(update, db)
        if not go_getter:
            return

        tasks = await crud_task.get_tasks_for_day(db, go_getter.id, date.today())
        if not tasks:
            await update.message.reply_text(  # type: ignore[union-attr]
                "No tasks scheduled for today. Enjoy your rest day!"
            )
            return

        lines = [f"*Today's tasks for {go_getter.display_name}:*\n"]
        keyboard = []
        for task in tasks:
            ci = await crud_check_in.get_by_task_and_go_getter(db, task.id, go_getter.id)
            status_icon = {"completed": "✅", "skipped": "⏭"}.get(
                ci.status.value if ci else "", "⬜"
            )
            lines.append(
                f"{status_icon} *{task.id}* — {task.title} "
                f"({task.estimated_minutes} min, {task.xp_reward} XP)"
            )
            if not ci:
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            f"✅ Done #{task.id}", callback_data=f"done:{task.id}"
                        ),
                        InlineKeyboardButton(f"⏭ Skip #{task.id}", callback_data=f"skip:{task.id}"),
                    ]
                )

        await update.message.reply_text(  # type: ignore[union-attr]
            "\n".join(lines),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
        )


async def cmd_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if not args or not args[0].isdigit():
        await update.message.reply_text("Usage: /checkin <task_id>")  # type: ignore[union-attr]
        return

    task_id = int(args[0])
    async with AsyncSessionLocal() as db:
        go_getter = await _get_go_getter_or_reply(update, db)
        if not go_getter:
            return
        await _do_checkin(update, db, go_getter, task_id)


async def cmd_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if not args or not args[0].isdigit():
        await update.message.reply_text("Usage: /skip <task_id> [reason]")  # type: ignore[union-attr]
        return

    task_id = int(args[0])
    reason = " ".join(args[1:]) if len(args) > 1 else None
    async with AsyncSessionLocal() as db:
        go_getter = await _get_go_getter_or_reply(update, db)
        if not go_getter:
            return
        await _do_skip(update, db, go_getter, task_id, reason)


async def cmd_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(  # type: ignore[union-attr]
        "Unknown command. Try /today, /checkin <id>, or /skip <id>."
    )


# ---------------------------------------------------------------------------
# Callback query handlers (inline keyboard buttons)
# ---------------------------------------------------------------------------


async def cb_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()  # type: ignore[union-attr]
    task_id = int(query.data.split(":")[1])  # type: ignore[union-attr]
    async with AsyncSessionLocal() as db:
        go_getter = await crud_go_getter.get_by_chat_id(db, update.effective_user.id)  # type: ignore[union-attr]
        if not go_getter:
            await query.edit_message_text("You are not registered.")  # type: ignore[union-attr]
            return
        await _do_checkin(update, db, go_getter, task_id, via_callback=True)


async def cb_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()  # type: ignore[union-attr]
    task_id = int(query.data.split(":")[1])  # type: ignore[union-attr]
    async with AsyncSessionLocal() as db:
        go_getter = await crud_go_getter.get_by_chat_id(db, update.effective_user.id)  # type: ignore[union-attr]
        if not go_getter:
            await query.edit_message_text("You are not registered.")  # type: ignore[union-attr]
            return
        await _do_skip(update, db, go_getter, task_id, reason=None, via_callback=True)


# ---------------------------------------------------------------------------
# Shared business logic
# ---------------------------------------------------------------------------


async def _do_checkin(
    update: Update,
    db,
    go_getter: GoGetter,
    task_id: int,
    mood_score: int = 3,
    via_callback: bool = False,
) -> None:
    task = await crud_task.get_with_ownership(db, task_id, go_getter.id)
    if not task:
        msg = f"Task #{task_id} not found or not yours."
        if via_callback:
            await update.callback_query.edit_message_text(msg)  # type: ignore[union-attr]
        else:
            await update.message.reply_text(msg)  # type: ignore[union-attr]
        return
    eligible = await crud_task.get_eligible_for_date(db, task_id, go_getter.id, date.today())
    if not eligible:
        msg = f"Task #{task_id} is not scheduled for today."
        if via_callback:
            await update.callback_query.edit_message_text(msg)  # type: ignore[union-attr]
        else:
            await update.message.reply_text(msg)  # type: ignore[union-attr]
        return

    existing = await crud_check_in.get_by_task_and_go_getter(db, task_id, go_getter.id)
    if existing:
        msg = f"Task #{task_id} already recorded as *{existing.status.value}*."
        if via_callback:
            await update.callback_query.edit_message_text(msg, parse_mode="Markdown")  # type: ignore[union-attr]
        else:
            await update.message.reply_text(msg, parse_mode="Markdown")  # type: ignore[union-attr]
        return

    xp_result = await streak_service.update_streak_and_xp(
        db=db,
        go_getter=go_getter,
        base_xp=task.xp_reward,
        mood_score=mood_score,
        check_in_date=date.today(),
    )
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
        xp_earned=xp_result.xp_earned,
        streak_at_checkin=xp_result.new_streak,
        praise_message=praise,
    )
    db.add(check_in)

    from sqlalchemy import update as sa_update
    from app.models.weekly_milestone import WeeklyMilestone

    await db.execute(
        sa_update(WeeklyMilestone)
        .where(WeeklyMilestone.id == task.milestone_id)
        .values(completed_tasks=WeeklyMilestone.completed_tasks + 1)
    )
    await db.commit()

    badge_text = ""
    if xp_result.badges_earned:
        badge_text = "\n🏅 " + " ".join(xp_result.badges_earned)

    msg = (
        f"✅ *{task.title}* checked in!\n"
        f"+{xp_result.xp_earned} XP | streak {xp_result.new_streak} 🔥\n\n"
        f"_{praise}_{badge_text}"
    )
    if via_callback:
        await update.callback_query.edit_message_text(msg, parse_mode="Markdown")  # type: ignore[union-attr]
    else:
        await update.message.reply_text(msg, parse_mode="Markdown")  # type: ignore[union-attr]


async def _do_skip(
    update: Update,
    db,
    go_getter: GoGetter,
    task_id: int,
    reason: Optional[str],
    via_callback: bool = False,
) -> None:
    task = await crud_task.get_with_ownership(db, task_id, go_getter.id)
    if not task:
        msg = f"Task #{task_id} not found or not yours."
        if via_callback:
            await update.callback_query.edit_message_text(msg)  # type: ignore[union-attr]
        else:
            await update.message.reply_text(msg)  # type: ignore[union-attr]
        return
    eligible = await crud_task.get_eligible_for_date(db, task_id, go_getter.id, date.today())
    if not eligible:
        msg = f"Task #{task_id} is not scheduled for today."
        if via_callback:
            await update.callback_query.edit_message_text(msg)  # type: ignore[union-attr]
        else:
            await update.message.reply_text(msg)  # type: ignore[union-attr]
        return

    existing = await crud_check_in.get_by_task_and_go_getter(db, task_id, go_getter.id)
    if existing:
        msg = f"Task #{task_id} already recorded as *{existing.status.value}*."
        if via_callback:
            await update.callback_query.edit_message_text(msg, parse_mode="Markdown")  # type: ignore[union-attr]
        else:
            await update.message.reply_text(msg, parse_mode="Markdown")  # type: ignore[union-attr]
        return

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

    msg = f"⏭ *{task.title}* skipped."
    if reason:
        msg += f"\nReason: _{reason}_"
    if via_callback:
        await update.callback_query.edit_message_text(msg, parse_mode="Markdown")  # type: ignore[union-attr]
    else:
        await update.message.reply_text(msg, parse_mode="Markdown")  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def start_go_getter_bot() -> None:
    """Build and run the bot in polling mode (blocking coroutine).

    Designed to be wrapped in asyncio.create_task() from the FastAPI lifespan.
    Cancellation (CancelledError) is the expected shutdown signal.
    """
    token = settings.TELEGRAM_GO_GETTER_BOT_TOKEN
    if not token:
        logger.info("TELEGRAM_GO_GETTER_BOT_TOKEN not set – go getter bot not started")
        return

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("checkin", cmd_checkin))
    app.add_handler(CommandHandler("skip", cmd_skip))
    app.add_handler(CallbackQueryHandler(cb_done, pattern=r"^done:\d+$"))
    app.add_handler(CallbackQueryHandler(cb_skip, pattern=r"^skip:\d+$"))
    app.add_handler(MessageHandler(filters.COMMAND, cmd_unknown))

    logger.info("Starting Telegram go getter bot (polling)…")
    async with app:
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)  # type: ignore[union-attr]
        # Run until the task is cancelled
        try:
            import asyncio

            while True:
                await asyncio.sleep(3600)
        finally:
            await app.updater.stop()  # type: ignore[union-attr]
            await app.stop()
