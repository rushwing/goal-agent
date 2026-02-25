"""Tests for issue #2: best_pal–go_getter ownership model."""

import pytest
import pytest_asyncio

from app.crud.go_getters import crud_go_getter
from app.crud.best_pals import crud_best_pal
from app.models.best_pal import BestPal
from app.models.go_getter import GoGetter
from app.schemas.go_getter import GoGetterCreate


@pytest_asyncio.fixture
async def two_families(db):
    best_pal_a = BestPal(name="BestPalA", telegram_chat_id=3001, is_admin=False)
    best_pal_b = BestPal(name="BestPalB", telegram_chat_id=3002, is_admin=False)
    db.add_all([best_pal_a, best_pal_b])
    await db.flush()

    go_getter_a = await crud_go_getter.create(
        db,
        obj_in=GoGetterCreate(
            name="Alice",
            display_name="Alice",
            grade="5",
            telegram_chat_id=4001,
            best_pal_id=best_pal_a.id,
        ),
    )
    go_getter_b = await crud_go_getter.create(
        db,
        obj_in=GoGetterCreate(
            name="Bob",
            display_name="Bob",
            grade="6",
            telegram_chat_id=4002,
            best_pal_id=best_pal_b.id,
        ),
    )
    return best_pal_a, best_pal_b, go_getter_a, go_getter_b


@pytest.mark.asyncio
async def test_create_go_getter_persists_best_pal_id(db, two_families):
    """crud_go_getter.create() must persist best_pal_id."""
    best_pal_a, _, go_getter_a, _ = two_families
    fetched = await crud_go_getter.get(db, go_getter_a.id)
    assert fetched.best_pal_id == best_pal_a.id


@pytest.mark.asyncio
async def test_get_by_best_pal_returns_own_go_getters(db, two_families):
    best_pal_a, best_pal_b, go_getter_a, go_getter_b = two_families
    go_getters_a = await crud_go_getter.get_by_best_pal(db, best_pal_a.id)
    ids_a = {g.id for g in go_getters_a}
    assert go_getter_a.id in ids_a
    assert go_getter_b.id not in ids_a


@pytest.mark.asyncio
async def test_get_by_best_pal_isolation(db, two_families):
    best_pal_a, best_pal_b, go_getter_a, go_getter_b = two_families
    go_getters_b = await crud_go_getter.get_by_best_pal(db, best_pal_b.id)
    ids_b = {g.id for g in go_getters_b}
    assert go_getter_b.id in ids_b
    assert go_getter_a.id not in ids_b


@pytest.mark.asyncio
async def test_go_getter_without_best_pal_id(db):
    """Go getters may be created without a best_pal_id (nullable FK)."""
    go_getter = await crud_go_getter.create(
        db,
        obj_in=GoGetterCreate(
            name="Orphan",
            display_name="Orphan",
            grade="3",
            telegram_chat_id=5999,
        ),
    )
    fetched = await crud_go_getter.get(db, go_getter.id)
    assert fetched.best_pal_id is None
