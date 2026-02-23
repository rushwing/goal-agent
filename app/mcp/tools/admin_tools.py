"""Admin MCP tools: manage pupils and parents (role: admin)."""
from typing import Optional

from app.database import AsyncSessionLocal
from app.mcp.auth import Role, require_role
from app.mcp.server import mcp
from app.crud import crud_pupil, crud_parent
from app.schemas.pupil import PupilCreate, PupilUpdate
from app.schemas.parent import ParentCreate, ParentUpdate


def _require_chat_id(chat_id: Optional[int]) -> int:
    if chat_id is None:
        raise ValueError("X-Telegram-Chat-Id header is required")
    return chat_id


@mcp.tool()
async def add_pupil(
    name: str,
    display_name: str,
    grade: str,
    telegram_chat_id: int,
    x_telegram_chat_id: Optional[int] = None,
    parent_id: Optional[int] = None,
) -> dict:
    """Add a new pupil. Requires admin role."""
    caller_id = _require_chat_id(x_telegram_chat_id)
    async with AsyncSessionLocal() as db:
        await require_role(db, caller_id, [Role.admin])
        schema = PupilCreate(
            name=name,
            display_name=display_name,
            grade=grade,
            telegram_chat_id=telegram_chat_id,
            parent_id=parent_id,
        )
        pupil = await crud_pupil.create(db, obj_in=schema)
        await db.commit()
        return {
            "id": pupil.id,
            "name": pupil.name,
            "display_name": pupil.display_name,
            "grade": pupil.grade,
            "telegram_chat_id": pupil.telegram_chat_id,
            "is_active": pupil.is_active,
        }


@mcp.tool()
async def update_pupil(
    pupil_id: int,
    name: Optional[str] = None,
    display_name: Optional[str] = None,
    grade: Optional[str] = None,
    telegram_chat_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    x_telegram_chat_id: Optional[int] = None,
) -> dict:
    """Update a pupil's details. Requires admin role."""
    caller_id = _require_chat_id(x_telegram_chat_id)
    async with AsyncSessionLocal() as db:
        await require_role(db, caller_id, [Role.admin])
        pupil = await crud_pupil.get(db, pupil_id)
        if not pupil:
            raise ValueError(f"Pupil {pupil_id} not found")
        schema = PupilUpdate(
            name=name, display_name=display_name, grade=grade,
            telegram_chat_id=telegram_chat_id, is_active=is_active
        )
        pupil = await crud_pupil.update(db, db_obj=pupil, obj_in=schema)
        await db.commit()
        return {"id": pupil.id, "name": pupil.name, "is_active": pupil.is_active}


@mcp.tool()
async def remove_pupil(
    pupil_id: int,
    x_telegram_chat_id: Optional[int] = None,
) -> dict:
    """Deactivate a pupil (soft delete). Requires admin role."""
    caller_id = _require_chat_id(x_telegram_chat_id)
    async with AsyncSessionLocal() as db:
        await require_role(db, caller_id, [Role.admin])
        pupil = await crud_pupil.get(db, pupil_id)
        if not pupil:
            raise ValueError(f"Pupil {pupil_id} not found")
        pupil.is_active = False
        await db.flush()
        await db.commit()
        return {"success": True, "pupil_id": pupil_id}


@mcp.tool()
async def list_pupils(
    x_telegram_chat_id: Optional[int] = None,
) -> list[dict]:
    """List all pupils. Requires admin role."""
    caller_id = _require_chat_id(x_telegram_chat_id)
    async with AsyncSessionLocal() as db:
        await require_role(db, caller_id, [Role.admin])
        pupils = await crud_pupil.get_multi(db)
        return [
            {
                "id": p.id,
                "name": p.name,
                "display_name": p.display_name,
                "grade": p.grade,
                "telegram_chat_id": p.telegram_chat_id,
                "xp_total": p.xp_total,
                "streak_current": p.streak_current,
                "is_active": p.is_active,
            }
            for p in pupils
        ]


@mcp.tool()
async def add_parent(
    name: str,
    telegram_chat_id: int,
    is_admin: bool = False,
    x_telegram_chat_id: Optional[int] = None,
) -> dict:
    """Add a new parent. Requires admin role."""
    caller_id = _require_chat_id(x_telegram_chat_id)
    async with AsyncSessionLocal() as db:
        await require_role(db, caller_id, [Role.admin])
        schema = ParentCreate(name=name, telegram_chat_id=telegram_chat_id, is_admin=is_admin)
        parent = await crud_parent.create(db, obj_in=schema)
        await db.commit()
        return {"id": parent.id, "name": parent.name, "is_admin": parent.is_admin}


@mcp.tool()
async def update_parent(
    parent_id: int,
    name: Optional[str] = None,
    telegram_chat_id: Optional[int] = None,
    is_admin: Optional[bool] = None,
    x_telegram_chat_id: Optional[int] = None,
) -> dict:
    """Update a parent. Requires admin role."""
    caller_id = _require_chat_id(x_telegram_chat_id)
    async with AsyncSessionLocal() as db:
        await require_role(db, caller_id, [Role.admin])
        parent = await crud_parent.get(db, parent_id)
        if not parent:
            raise ValueError(f"Parent {parent_id} not found")
        schema = ParentUpdate(name=name, telegram_chat_id=telegram_chat_id, is_admin=is_admin)
        parent = await crud_parent.update(db, db_obj=parent, obj_in=schema)
        await db.commit()
        return {"id": parent.id, "name": parent.name, "is_admin": parent.is_admin}


@mcp.tool()
async def remove_parent(
    parent_id: int,
    x_telegram_chat_id: Optional[int] = None,
) -> dict:
    """Remove a parent. Requires admin role."""
    caller_id = _require_chat_id(x_telegram_chat_id)
    async with AsyncSessionLocal() as db:
        await require_role(db, caller_id, [Role.admin])
        parent = await crud_parent.remove(db, id=parent_id)
        if not parent:
            raise ValueError(f"Parent {parent_id} not found")
        await db.commit()
        return {"success": True, "parent_id": parent_id}


@mcp.tool()
async def list_parents(
    x_telegram_chat_id: Optional[int] = None,
) -> list[dict]:
    """List all parents. Requires admin role."""
    caller_id = _require_chat_id(x_telegram_chat_id)
    async with AsyncSessionLocal() as db:
        await require_role(db, caller_id, [Role.admin])
        parents = await crud_parent.get_multi(db)
        return [
            {"id": p.id, "name": p.name, "telegram_chat_id": p.telegram_chat_id, "is_admin": p.is_admin}
            for p in parents
        ]
