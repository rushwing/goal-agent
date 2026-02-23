"""Tests for issue #2: parent-pupil ownership model."""
import pytest
import pytest_asyncio

from app.crud.pupils import crud_pupil
from app.crud.parents import crud_parent
from app.models.parent import Parent
from app.models.pupil import Pupil
from app.schemas.pupil import PupilCreate


@pytest_asyncio.fixture
async def two_families(db):
    parent_a = Parent(name="ParentA", telegram_chat_id=3001, is_admin=False)
    parent_b = Parent(name="ParentB", telegram_chat_id=3002, is_admin=False)
    db.add_all([parent_a, parent_b])
    await db.flush()

    pupil_a = await crud_pupil.create(
        db,
        obj_in=PupilCreate(
            name="Alice", display_name="Alice", grade="5",
            telegram_chat_id=4001, parent_id=parent_a.id,
        ),
    )
    pupil_b = await crud_pupil.create(
        db,
        obj_in=PupilCreate(
            name="Bob", display_name="Bob", grade="6",
            telegram_chat_id=4002, parent_id=parent_b.id,
        ),
    )
    return parent_a, parent_b, pupil_a, pupil_b


@pytest.mark.asyncio
async def test_create_pupil_persists_parent_id(db, two_families):
    """crud_pupil.create() must now persist parent_id (was previously dropped)."""
    parent_a, _, pupil_a, _ = two_families
    fetched = await crud_pupil.get(db, pupil_a.id)
    assert fetched.parent_id == parent_a.id


@pytest.mark.asyncio
async def test_get_by_parent_returns_own_children(db, two_families):
    parent_a, parent_b, pupil_a, pupil_b = two_families
    children_a = await crud_pupil.get_by_parent(db, parent_a.id)
    ids_a = {p.id for p in children_a}
    assert pupil_a.id in ids_a
    assert pupil_b.id not in ids_a


@pytest.mark.asyncio
async def test_get_by_parent_isolation(db, two_families):
    parent_a, parent_b, pupil_a, pupil_b = two_families
    children_b = await crud_pupil.get_by_parent(db, parent_b.id)
    ids_b = {p.id for p in children_b}
    assert pupil_b.id in ids_b
    assert pupil_a.id not in ids_b


@pytest.mark.asyncio
async def test_pupil_without_parent_id(db):
    """Pupils may be created without a parent_id (nullable FK)."""
    pupil = await crud_pupil.create(
        db,
        obj_in=PupilCreate(
            name="Orphan", display_name="Orphan", grade="3",
            telegram_chat_id=5999,
        ),
    )
    fetched = await crud_pupil.get(db, pupil.id)
    assert fetched.parent_id is None
