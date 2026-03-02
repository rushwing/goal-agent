"""Admin MCP tools: manage go_getters and best_pals (role: admin)."""

from typing import Optional

from app.database import AsyncSessionLocal
from app.mcp.auth import Role, require_role
from app.mcp.server import mcp
from app.crud import crud_go_getter, crud_best_pal
from app.schemas.go_getter import GoGetterCreate, GoGetterUpdate
from app.schemas.best_pal import BestPalCreate, BestPalUpdate


def _require_chat_id(chat_id: Optional[int]) -> int:
    if chat_id is None:
        raise ValueError("X-Telegram-Chat-Id header is required")
    return chat_id


@mcp.tool()
async def add_go_getter(
    name: str,
    display_name: str,
    grade: str,
    telegram_chat_id: int,
    x_telegram_chat_id: Optional[int] = None,
    best_pal_id: Optional[int] = None,
) -> dict:
    """Add a new go getter. Requires admin role."""
    caller_id = _require_chat_id(x_telegram_chat_id)
    async with AsyncSessionLocal() as db:
        await require_role(db, caller_id, [Role.admin])
        schema = GoGetterCreate(
            name=name,
            display_name=display_name,
            grade=grade,
            telegram_chat_id=telegram_chat_id,
            best_pal_id=best_pal_id,
        )
        go_getter = await crud_go_getter.create(db, obj_in=schema)
        await db.commit()
        return {
            "id": go_getter.id,
            "name": go_getter.name,
            "display_name": go_getter.display_name,
            "grade": go_getter.grade,
            "telegram_chat_id": go_getter.telegram_chat_id,
            "is_active": go_getter.is_active,
        }


@mcp.tool()
async def update_go_getter(
    go_getter_id: int,
    name: Optional[str] = None,
    display_name: Optional[str] = None,
    grade: Optional[str] = None,
    telegram_chat_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    x_telegram_chat_id: Optional[int] = None,
) -> dict:
    """Update a go getter's details. Requires admin role."""
    caller_id = _require_chat_id(x_telegram_chat_id)
    async with AsyncSessionLocal() as db:
        await require_role(db, caller_id, [Role.admin])
        go_getter = await crud_go_getter.get(db, go_getter_id)
        if not go_getter:
            raise ValueError(f"Go getter {go_getter_id} not found")
        schema = GoGetterUpdate(
            name=name,
            display_name=display_name,
            grade=grade,
            telegram_chat_id=telegram_chat_id,
            is_active=is_active,
        )
        go_getter = await crud_go_getter.update(db, db_obj=go_getter, obj_in=schema)
        await db.commit()
        return {"id": go_getter.id, "name": go_getter.name, "is_active": go_getter.is_active}


@mcp.tool()
async def remove_go_getter(
    go_getter_id: int,
    x_telegram_chat_id: Optional[int] = None,
) -> dict:
    """Deactivate a go getter (soft delete). Requires admin role."""
    caller_id = _require_chat_id(x_telegram_chat_id)
    async with AsyncSessionLocal() as db:
        await require_role(db, caller_id, [Role.admin])
        go_getter = await crud_go_getter.get(db, go_getter_id)
        if not go_getter:
            raise ValueError(f"Go getter {go_getter_id} not found")
        go_getter.is_active = False
        await db.flush()
        await db.commit()
        return {"success": True, "go_getter_id": go_getter_id}


@mcp.tool()
async def list_go_getters(
    x_telegram_chat_id: Optional[int] = None,
) -> list[dict]:
    """List all go getters. Requires admin role."""
    caller_id = _require_chat_id(x_telegram_chat_id)
    async with AsyncSessionLocal() as db:
        await require_role(db, caller_id, [Role.admin])
        go_getters = await crud_go_getter.get_multi(db)
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
            for p in go_getters
        ]


@mcp.tool()
async def add_best_pal(
    name: str,
    telegram_chat_id: int,
    is_admin: bool = False,
    x_telegram_chat_id: Optional[int] = None,
) -> dict:
    """Add a new best pal. Requires admin role."""
    caller_id = _require_chat_id(x_telegram_chat_id)
    async with AsyncSessionLocal() as db:
        await require_role(db, caller_id, [Role.admin])
        schema = BestPalCreate(name=name, telegram_chat_id=telegram_chat_id, is_admin=is_admin)
        best_pal = await crud_best_pal.create(db, obj_in=schema)
        await db.commit()
        return {"id": best_pal.id, "name": best_pal.name, "is_admin": best_pal.is_admin}


@mcp.tool()
async def update_best_pal(
    best_pal_id: int,
    name: Optional[str] = None,
    telegram_chat_id: Optional[int] = None,
    is_admin: Optional[bool] = None,
    x_telegram_chat_id: Optional[int] = None,
) -> dict:
    """Update a best pal. Requires admin role."""
    caller_id = _require_chat_id(x_telegram_chat_id)
    async with AsyncSessionLocal() as db:
        await require_role(db, caller_id, [Role.admin])
        best_pal = await crud_best_pal.get(db, best_pal_id)
        if not best_pal:
            raise ValueError(f"Best pal {best_pal_id} not found")
        schema = BestPalUpdate(name=name, telegram_chat_id=telegram_chat_id, is_admin=is_admin)
        best_pal = await crud_best_pal.update(db, db_obj=best_pal, obj_in=schema)
        await db.commit()
        return {"id": best_pal.id, "name": best_pal.name, "is_admin": best_pal.is_admin}


@mcp.tool()
async def remove_best_pal(
    best_pal_id: int,
    x_telegram_chat_id: Optional[int] = None,
) -> dict:
    """Remove a best pal. Blocked if they still have go_getters assigned.

    Reassign all go_getters first via update_go_getter before calling this.
    Requires admin role.
    """
    from sqlalchemy import func, select
    from app.models.go_getter import GoGetter

    caller_id = _require_chat_id(x_telegram_chat_id)
    async with AsyncSessionLocal() as db:
        await require_role(db, caller_id, [Role.admin])
        best_pal = await crud_best_pal.get(db, best_pal_id)
        if not best_pal:
            raise ValueError(f"Best pal {best_pal_id} not found")
        result = await db.execute(
            select(func.count()).select_from(GoGetter).where(GoGetter.best_pal_id == best_pal_id)
        )
        go_getter_count = result.scalar_one()
        if go_getter_count > 0:
            raise ValueError(
                f"Best pal {best_pal_id} has {go_getter_count} go_getter(s) assigned. "
                "Reassign them first via update_go_getter with a new best_pal_id."
            )
        await crud_best_pal.remove(db, id=best_pal_id)
        await db.commit()
        return {"success": True, "best_pal_id": best_pal_id}


@mcp.tool()
async def list_best_pals(
    x_telegram_chat_id: Optional[int] = None,
) -> list[dict]:
    """List all best pals. Requires admin role."""
    caller_id = _require_chat_id(x_telegram_chat_id)
    async with AsyncSessionLocal() as db:
        await require_role(db, caller_id, [Role.admin])
        best_pals = await crud_best_pal.get_multi(db)
        return [
            {
                "id": p.id,
                "name": p.name,
                "telegram_chat_id": p.telegram_chat_id,
                "is_admin": p.is_admin,
            }
            for p in best_pals
        ]
