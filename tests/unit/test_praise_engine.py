"""Unit tests for offline praise templates."""
from app.services.praise_engine import get_offline_praise


def test_offline_praise_returns_string():
    for mood in range(1, 6):
        for streak in [1, 3, 7, 14, 30]:
            praise = get_offline_praise(mood, streak)
            assert isinstance(praise, str)
            assert len(praise) > 10


def test_offline_praise_high_streak():
    praise = get_offline_praise(5, 30)
    assert praise  # should not be empty
