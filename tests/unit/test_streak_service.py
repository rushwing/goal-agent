"""Unit tests for streak and XP calculation."""
import pytest
from app.services.streak_service import calculate_xp


@pytest.mark.parametrize("base_xp,streak,mood,expected", [
    (10, 1, 3, 10),      # no multiplier, neutral mood
    (10, 7, 5, 18),      # 1.5x streak * 1.2 mood = 18
    (10, 14, 5, 24),     # 2.0x streak * 1.2 mood = 24
    (10, 3, 1, 10),      # 1.2x streak * 0.8 mood = 9.6 → round(9.6) = 10
    (10, 1, 1, 8),       # 1.0x * 0.8 = 8
])
def test_calculate_xp(base_xp, streak, mood, expected):
    result = calculate_xp(base_xp, streak, mood)
    assert result == expected
