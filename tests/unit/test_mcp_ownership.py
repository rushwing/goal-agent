"""Tests for issue #17: MCP best_pal ownership enforcement via verify_best_pal_owns_go_getter."""

import pytest
import pytest_asyncio

from app.models.best_pal import BestPal
from app.models.go_getter import GoGetter
from app.mcp.auth import verify_best_pal_owns_go_getter


@pytest_asyncio.fixture
async def two_families(db):
    admin = BestPal(name="Admin", telegram_chat_id=8000, is_admin=True)
    best_pal_a = BestPal(name="ParentA", telegram_chat_id=8001, is_admin=False)
    best_pal_b = BestPal(name="ParentB", telegram_chat_id=8002, is_admin=False)
    db.add_all([admin, best_pal_a, best_pal_b])
    await db.flush()

    go_getter_a = GoGetter(
        best_pal_id=best_pal_a.id,
        name="Alice",
        display_name="Alice",
        grade="5",
        telegram_chat_id=9001,
    )
    go_getter_b = GoGetter(
        best_pal_id=best_pal_b.id,
        name="Bob",
        display_name="Bob",
        grade="6",
        telegram_chat_id=9002,
    )
    db.add_all([go_getter_a, go_getter_b])
    await db.flush()
    return admin, best_pal_a, best_pal_b, go_getter_a, go_getter_b


@pytest.mark.asyncio
async def test_best_pal_cannot_access_other_family(db, two_families):
    """best_pal accessing another family's go_getter must raise PermissionError."""
    _, best_pal_a, _, _, go_getter_b = two_families
    with pytest.raises(PermissionError, match="Not authorized"):
        await verify_best_pal_owns_go_getter(db, best_pal_a.telegram_chat_id, go_getter_b.id)


@pytest.mark.asyncio
async def test_best_pal_can_access_own_go_getter(db, two_families):
    """best_pal accessing their own go_getter must succeed."""
    _, best_pal_a, _, go_getter_a, _ = two_families
    # Should not raise
    await verify_best_pal_owns_go_getter(db, best_pal_a.telegram_chat_id, go_getter_a.id)


@pytest.mark.asyncio
async def test_admin_can_access_any_go_getter(db, two_families):
    """Admin must be able to access any go_getter regardless of family."""
    admin, _, _, go_getter_a, go_getter_b = two_families
    await verify_best_pal_owns_go_getter(db, admin.telegram_chat_id, go_getter_a.id)
    await verify_best_pal_owns_go_getter(db, admin.telegram_chat_id, go_getter_b.id)


@pytest.mark.asyncio
async def test_nonexistent_go_getter_raises_value_error(db, two_families):
    """Accessing a go_getter that doesn't exist must raise ValueError."""
    _, best_pal_a, _, _, _ = two_families
    with pytest.raises(ValueError, match="Go getter not found"):
        await verify_best_pal_owns_go_getter(db, best_pal_a.telegram_chat_id, 99999)
