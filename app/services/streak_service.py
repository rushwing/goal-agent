"""Streak and XP logic."""

from datetime import date, timedelta
from typing import NamedTuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.go_getter import GoGetter
from app.models.achievement import Achievement


BADGE_CATALOGUE = {
    "first_checkin": ("First Step!", "🌟", 10),
    "streak_3": ("3-Day Streak!", "🔥", 15),
    "streak_7": ("Week Warrior!", "🦁", 30),
    "streak_14": ("Fortnight Champion!", "🏆", 75),
    "streak_30": ("Monthly Master!", "👑", 200),
    "xp_50": ("50 XP Club!", "⭐", 5),
    "xp_100": ("Century Scholar!", "💯", 10),
    "xp_500": ("XP Legend!", "🎖️", 50),
    "weekend_warrior": ("Weekend Warrior!", "🏄", 20),
}


class XPResult(NamedTuple):
    xp_earned: int
    new_streak: int
    badges_earned: list[str]


def calculate_xp(base_xp: int, streak: int, mood_score: int) -> int:
    """Apply streak multiplier and mood bonus."""
    if streak <= 2:
        streak_mult = 1.0
    elif streak <= 6:
        streak_mult = 1.2
    elif streak <= 13:
        streak_mult = 1.5
    else:
        streak_mult = 2.0

    mood_bonuses = {1: 0.8, 2: 0.9, 3: 1.0, 4: 1.1, 5: 1.2}
    mood_mult = mood_bonuses.get(mood_score, 1.0)

    return max(1, round(base_xp * streak_mult * mood_mult))


async def update_streak_and_xp(
    db: AsyncSession,
    go_getter: GoGetter,
    base_xp: int,
    mood_score: int,
    check_in_date: date,
) -> XPResult:
    """
    Update go getter streak and XP. Returns earned XP and any new badges.
    """
    today = check_in_date
    last = go_getter.streak_last_date

    if last is None:
        new_streak = 1
    elif last == today:
        # Already checked in today; don't increment streak
        new_streak = go_getter.streak_current
    elif last == today - timedelta(days=1):
        new_streak = go_getter.streak_current + 1
    else:
        # Streak broken
        new_streak = 1

    xp_earned = calculate_xp(base_xp, new_streak, mood_score)

    go_getter.streak_current = new_streak
    if new_streak > go_getter.streak_longest:
        go_getter.streak_longest = new_streak
    go_getter.streak_last_date = today
    go_getter.xp_total += xp_earned
    db.add(go_getter)

    badges_earned = await _check_achievements(db, go_getter, new_streak, xp_earned)

    return XPResult(xp_earned=xp_earned, new_streak=new_streak, badges_earned=badges_earned)


async def _check_achievements(
    db: AsyncSession,
    go_getter: GoGetter,
    new_streak: int,
    xp_just_earned: int,
) -> list[str]:
    """Unlock new achievement badges and return their keys."""
    from app.crud.achievements import crud_achievement

    earned: list[str] = []

    candidates: list[str] = []

    # First check-in
    if go_getter.xp_total == xp_just_earned:  # first ever XP
        candidates.append("first_checkin")

    # Streak milestones
    for days, key in [(3, "streak_3"), (7, "streak_7"), (14, "streak_14"), (30, "streak_30")]:
        if new_streak >= days:
            candidates.append(key)

    # XP milestones
    for threshold, key in [(50, "xp_50"), (100, "xp_100"), (500, "xp_500")]:
        if go_getter.xp_total >= threshold:
            candidates.append(key)

    # Weekend warrior
    today = go_getter.streak_last_date
    if today and today.weekday() in (5, 6):  # Sat or Sun
        candidates.append("weekend_warrior")

    total_bonus = 0
    for badge_key in candidates:
        if not await crud_achievement.has_badge(db, go_getter.id, badge_key):
            name, icon, bonus = BADGE_CATALOGUE[badge_key]
            achievement = Achievement(
                go_getter_id=go_getter.id,
                badge_key=badge_key,
                badge_name=name,
                badge_icon=icon,
                xp_bonus=bonus,
            )
            db.add(achievement)
            total_bonus += bonus
            earned.append(badge_key)

    if total_bonus:
        go_getter.xp_total += total_bonus
        db.add(go_getter)

    return earned
