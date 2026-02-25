"""Tests for issues #5 and #6: idempotent report generation and period filtering."""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from app.models.best_pal import BestPal
from app.models.go_getter import GoGetter
from app.models.check_in import CheckIn, CheckInStatus
from app.models.report import Report, ReportType
from app.crud.reports import crud_report


@pytest_asyncio.fixture
async def go_getter(db):
    best_pal = BestPal(name="P2", telegram_chat_id=7001, is_admin=False)
    db.add(best_pal)
    await db.flush()
    g = GoGetter(
        best_pal_id=best_pal.id,
        name="Diana",
        display_name="Diana",
        grade="6",
        telegram_chat_id=7002,
    )
    db.add(g)
    await db.flush()
    return g


# ---------------------------------------------------------------------------
# Issue #5: idempotency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_daily_report_is_idempotent(db, go_getter):
    """Calling generate_daily_report twice must return the same report id."""
    report_date = date.today()
    fake_md = "# Report\n\nGood job."

    with (
        patch(
            "app.services.report_service.llm_service.chat_complete",
            new_callable=AsyncMock,
            return_value=(fake_md, 10, 20),
        ),
        patch(
            "app.services.report_service.github_service.commit_report",
            new_callable=AsyncMock,
            return_value=("abc123", "reports/file.md"),
        ),
    ):
        from app.services.report_service import generate_daily_report

        r1 = await generate_daily_report(db, go_getter, report_date)
        r2 = await generate_daily_report(db, go_getter, report_date)

    assert r1.id == r2.id, "Repeated calls must return the same report (idempotent)"


@pytest.mark.asyncio
async def test_weekly_report_is_idempotent(db, go_getter):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    fake_md = "# Weekly"

    with (
        patch(
            "app.services.report_service.llm_service.chat_complete",
            new_callable=AsyncMock,
            return_value=(fake_md, 10, 20),
        ),
        patch(
            "app.services.report_service.github_service.commit_report",
            new_callable=AsyncMock,
            return_value=("sha", "path"),
        ),
    ):
        from app.services.report_service import generate_weekly_report

        r1 = await generate_weekly_report(db, go_getter, week_start)
        r2 = await generate_weekly_report(db, go_getter, week_start)

    assert r1.id == r2.id


@pytest.mark.asyncio
async def test_monthly_report_is_idempotent(db, go_getter):
    today = date.today()
    fake_md = "# Monthly"

    with (
        patch(
            "app.services.report_service.llm_service.chat_complete",
            new_callable=AsyncMock,
            return_value=(fake_md, 10, 20),
        ),
        patch(
            "app.services.report_service.github_service.commit_report",
            new_callable=AsyncMock,
            return_value=("sha", "path"),
        ),
    ):
        from app.services.report_service import generate_monthly_report

        r1 = await generate_monthly_report(db, go_getter, today.year, today.month)
        r2 = await generate_monthly_report(db, go_getter, today.year, today.month)

    assert r1.id == r2.id


# ---------------------------------------------------------------------------
# Issue #6: period filtering uses actual check-in timestamp
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_check_ins_filters_by_created_at(db, go_getter):
    """Check-ins must be filtered by their created_at date, not milestone coverage."""
    today = date.today()
    yesterday = today - timedelta(days=1)

    # Set created_at explicitly to avoid relying on server_default in SQLite
    ci_today = CheckIn(
        task_id=1,
        go_getter_id=go_getter.id,
        status=CheckInStatus.completed,
        xp_earned=10,
        streak_at_checkin=1,
        created_at=datetime.combine(today, datetime.min.time()),
        updated_at=datetime.combine(today, datetime.min.time()),
    )
    ci_yesterday = CheckIn(
        task_id=2,
        go_getter_id=go_getter.id,
        status=CheckInStatus.completed,
        xp_earned=5,
        streak_at_checkin=1,
        created_at=datetime.combine(yesterday, datetime.min.time()),
        updated_at=datetime.combine(yesterday, datetime.min.time()),
    )
    db.add_all([ci_today, ci_yesterday])
    await db.flush()

    from app.services.report_service import _fetch_check_ins

    only_today = await _fetch_check_ins(db, go_getter.id, today, today)
    ids = {c.id for c in only_today}
    assert ci_today.id in ids, "Today's check-in must be included"
    assert ci_yesterday.id not in ids, "Yesterday's check-in must be excluded from daily filter"


@pytest.mark.asyncio
async def test_daily_report_excludes_other_days(db, go_getter):
    """Daily report stats must only count check-ins from the target day."""
    today = date.today()
    yesterday = today - timedelta(days=1)

    ci_today = CheckIn(
        task_id=10,
        go_getter_id=go_getter.id,
        status=CheckInStatus.completed,
        xp_earned=15,
        streak_at_checkin=2,
        created_at=datetime.combine(today, datetime.min.time()),
        updated_at=datetime.combine(today, datetime.min.time()),
    )
    ci_yesterday = CheckIn(
        task_id=11,
        go_getter_id=go_getter.id,
        status=CheckInStatus.completed,
        xp_earned=20,
        streak_at_checkin=1,
        created_at=datetime.combine(yesterday, datetime.min.time()),
        updated_at=datetime.combine(yesterday, datetime.min.time()),
    )
    db.add_all([ci_today, ci_yesterday])
    await db.flush()

    fake_md = "# Daily"
    with (
        patch(
            "app.services.report_service.llm_service.chat_complete",
            new_callable=AsyncMock,
            return_value=(fake_md, 5, 10),
        ),
        patch(
            "app.services.report_service.github_service.commit_report",
            new_callable=AsyncMock,
            return_value=("sha", "path"),
        ),
    ):
        from app.services.report_service import generate_daily_report

        report = await generate_daily_report(db, go_getter, today)

    # Only today's check-in (xp=15) should be counted
    assert report.xp_earned == 15, (
        f"Daily report must only include today's XP (15), got {report.xp_earned}"
    )
    assert report.tasks_completed == 1
