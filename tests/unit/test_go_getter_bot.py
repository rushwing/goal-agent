"""Unit tests for app.bots.go_getter_bot (Issue #8).

Uses unittest.mock to isolate every external dependency:
  - telegram.Update / telegram.ext.ContextTypes objects
  - AsyncSessionLocal (DB)
  - crud_go_getter, crud_task, crud_check_in
  - streak_service, praise_engine

No real Telegram API calls and no DB connection are made.
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Minimal stub builders
# ---------------------------------------------------------------------------


def _make_update(user_id: int = 1, text: str = "", args: list[str] | None = None):
    """Build a minimal Update-like object with a reply-capturing message."""
    message = MagicMock()
    message.reply_text = AsyncMock()
    update = MagicMock()
    update.effective_user = SimpleNamespace(id=user_id)
    update.message = message
    return update


def _make_context(args: list[str] | None = None):
    ctx = MagicMock()
    ctx.args = args or []
    return ctx


def _make_go_getter(chat_id: int = 1, name: str = "Alice"):
    return SimpleNamespace(
        id=10,
        telegram_chat_id=chat_id,
        display_name=name,
        grade="5",
        streak_current=3,
        xp_total=50,
    )


def _make_task(task_id: int = 7, milestone_id: int = 1):
    return SimpleNamespace(
        id=task_id,
        title="Read chapter 3",
        description="",
        estimated_minutes=30,
        xp_reward=10,
        task_type=SimpleNamespace(value="reading"),
        is_optional=False,
        day_of_week=date.today().weekday(),
        milestone_id=milestone_id,
    )


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cmd_start_sends_welcome():
    from app.bots.go_getter_bot import cmd_start

    update = _make_update()
    ctx = _make_context()
    await cmd_start(update, ctx)
    update.message.reply_text.assert_awaited_once()
    call_text = update.message.reply_text.call_args[0][0]
    assert "/today" in call_text


# ---------------------------------------------------------------------------
# /today — registered go getter with tasks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cmd_today_shows_tasks():
    from app.bots.go_getter_bot import cmd_today

    go_getter = _make_go_getter()
    task = _make_task()
    update = _make_update(user_id=go_getter.telegram_chat_id)
    ctx = _make_context()

    with (
        patch("app.bots.go_getter_bot.AsyncSessionLocal") as mock_session_cls,
        patch("app.bots.go_getter_bot.crud_go_getter") as mock_crud_go_getter,
        patch("app.bots.go_getter_bot.crud_task") as mock_crud_task,
        patch("app.bots.go_getter_bot.crud_check_in") as mock_crud_ci,
    ):
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_crud_go_getter.get_by_chat_id = AsyncMock(return_value=go_getter)
        mock_crud_task.get_tasks_for_day = AsyncMock(return_value=[task])
        mock_crud_ci.get_by_task_and_go_getter = AsyncMock(return_value=None)

        await cmd_today(update, ctx)

    update.message.reply_text.assert_awaited_once()
    text = update.message.reply_text.call_args[0][0]
    assert "Read chapter 3" in text


# ---------------------------------------------------------------------------
# /today — unregistered go getter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cmd_today_unregistered_go_getter():
    from app.bots.go_getter_bot import cmd_today

    update = _make_update(user_id=9999)
    ctx = _make_context()

    with (
        patch("app.bots.go_getter_bot.AsyncSessionLocal") as mock_session_cls,
        patch("app.bots.go_getter_bot.crud_go_getter") as mock_crud_go_getter,
    ):
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_crud_go_getter.get_by_chat_id = AsyncMock(return_value=None)

        await cmd_today(update, ctx)

    text = update.message.reply_text.call_args[0][0]
    assert "not registered" in text.lower()


# ---------------------------------------------------------------------------
# /today — no tasks today
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cmd_today_no_tasks():
    from app.bots.go_getter_bot import cmd_today

    go_getter = _make_go_getter()
    update = _make_update(user_id=go_getter.telegram_chat_id)
    ctx = _make_context()

    with (
        patch("app.bots.go_getter_bot.AsyncSessionLocal") as mock_session_cls,
        patch("app.bots.go_getter_bot.crud_go_getter") as mock_crud_go_getter,
        patch("app.bots.go_getter_bot.crud_task") as mock_crud_task,
    ):
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_crud_go_getter.get_by_chat_id = AsyncMock(return_value=go_getter)
        mock_crud_task.get_tasks_for_day = AsyncMock(return_value=[])

        await cmd_today(update, ctx)

    text = update.message.reply_text.call_args[0][0]
    assert "no tasks" in text.lower() or "rest day" in text.lower()


# ---------------------------------------------------------------------------
# /checkin <id>
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cmd_checkin_success():
    from app.bots.go_getter_bot import cmd_checkin

    go_getter = _make_go_getter()
    task = _make_task(task_id=7)
    xp_result = SimpleNamespace(xp_earned=12, new_streak=4, badges_earned=[])
    update = _make_update(user_id=go_getter.telegram_chat_id)
    ctx = _make_context(args=["7"])

    with (
        patch("app.bots.go_getter_bot.AsyncSessionLocal") as mock_session_cls,
        patch("app.bots.go_getter_bot.crud_go_getter") as mock_crud_go_getter,
        patch("app.bots.go_getter_bot.crud_task") as mock_crud_task,
        patch("app.bots.go_getter_bot.crud_check_in") as mock_crud_ci,
        patch("app.bots.go_getter_bot.streak_service") as mock_streak,
        patch("app.bots.go_getter_bot.praise_engine") as mock_praise,
    ):
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_crud_go_getter.get_by_chat_id = AsyncMock(return_value=go_getter)
        mock_crud_task.get = AsyncMock(return_value=task)
        mock_crud_ci.get_by_task_and_go_getter = AsyncMock(return_value=None)
        mock_streak.update_streak_and_xp = AsyncMock(return_value=xp_result)
        mock_praise.generate_praise = AsyncMock(return_value="Great work!")

        await cmd_checkin(update, ctx)

    text = update.message.reply_text.call_args[0][0]
    assert "checked in" in text.lower() or "✅" in text


@pytest.mark.asyncio
async def test_cmd_checkin_bad_args():
    from app.bots.go_getter_bot import cmd_checkin

    update = _make_update()
    ctx = _make_context(args=[])

    await cmd_checkin(update, ctx)

    text = update.message.reply_text.call_args[0][0]
    assert "usage" in text.lower() or "/checkin" in text.lower()


# ---------------------------------------------------------------------------
# /skip <id>
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cmd_skip_success():
    from app.bots.go_getter_bot import cmd_skip

    go_getter = _make_go_getter()
    task = _make_task(task_id=5)
    update = _make_update(user_id=go_getter.telegram_chat_id)
    ctx = _make_context(args=["5", "too", "hard"])

    with (
        patch("app.bots.go_getter_bot.AsyncSessionLocal") as mock_session_cls,
        patch("app.bots.go_getter_bot.crud_go_getter") as mock_crud_go_getter,
        patch("app.bots.go_getter_bot.crud_task") as mock_crud_task,
        patch("app.bots.go_getter_bot.crud_check_in") as mock_crud_ci,
    ):
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_crud_go_getter.get_by_chat_id = AsyncMock(return_value=go_getter)
        mock_crud_task.get = AsyncMock(return_value=task)
        mock_crud_ci.get_by_task_and_go_getter = AsyncMock(return_value=None)

        await cmd_skip(update, ctx)

    text = update.message.reply_text.call_args[0][0]
    assert "skipped" in text.lower() or "⏭" in text


# ---------------------------------------------------------------------------
# Already-recorded idempotency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cmd_checkin_already_recorded():
    from app.bots.go_getter_bot import cmd_checkin
    from app.models.check_in import CheckInStatus

    go_getter = _make_go_getter()
    task = _make_task(task_id=3)
    existing_ci = SimpleNamespace(status=CheckInStatus.completed, id=99)
    update = _make_update(user_id=go_getter.telegram_chat_id)
    ctx = _make_context(args=["3"])

    with (
        patch("app.bots.go_getter_bot.AsyncSessionLocal") as mock_session_cls,
        patch("app.bots.go_getter_bot.crud_go_getter") as mock_crud_go_getter,
        patch("app.bots.go_getter_bot.crud_task") as mock_crud_task,
        patch("app.bots.go_getter_bot.crud_check_in") as mock_crud_ci,
    ):
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_crud_go_getter.get_by_chat_id = AsyncMock(return_value=go_getter)
        mock_crud_task.get = AsyncMock(return_value=task)
        mock_crud_ci.get_by_task_and_go_getter = AsyncMock(return_value=existing_ci)

        await cmd_checkin(update, ctx)

    text = update.message.reply_text.call_args[0][0]
    assert "already" in text.lower()


# ---------------------------------------------------------------------------
# Unknown command
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cmd_unknown_replies():
    from app.bots.go_getter_bot import cmd_unknown

    update = _make_update()
    ctx = _make_context()
    await cmd_unknown(update, ctx)
    update.message.reply_text.assert_awaited_once()
