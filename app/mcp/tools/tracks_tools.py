"""Tracks MCP tools: list categories and subcategories (all authenticated roles)."""

from typing import Optional

from app.database import AsyncSessionLocal
from app.mcp.auth import Role, require_role
from app.mcp.server import mcp


def _require_chat_id(chat_id: Optional[int]) -> int:
    if chat_id is None:
        raise ValueError("X-Telegram-Chat-Id header is required")
    return chat_id


@mcp.tool()
async def list_track_categories(
    x_telegram_chat_id: Optional[int] = None,
) -> list[dict]:
    """List all track categories with their subcategories.

    Use this to discover subcategory_id values before creating targets or
    configuring wizard constraints.  Returns the full Study / Fitness / Habit
    / Mindset / Creative / Life Skills taxonomy.

    Accessible by admin, best_pal, and go_getter roles.
    """
    caller_id = _require_chat_id(x_telegram_chat_id)
    async with AsyncSessionLocal() as db:
        await require_role(db, caller_id, [Role.admin, Role.best_pal, Role.go_getter])
        from app.crud.tracks import get_all_categories

        categories = await get_all_categories(db)
        return [
            {
                "id": cat.id,
                "name": cat.name,
                "description": cat.description,
                "subcategories": [
                    {
                        "id": sub.id,
                        "name": sub.name,
                        "description": sub.description,
                    }
                    for sub in cat.subcategories
                ],
            }
            for cat in categories
        ]


@mcp.tool()
async def list_track_subcategories(
    category_id: Optional[int] = None,
    x_telegram_chat_id: Optional[int] = None,
) -> list[dict]:
    """List track subcategories, optionally filtered by category_id.

    Each entry includes id and name so you can pass subcategory_id to
    create_target or use it as a constraint key in set_wizard_constraints.

    Accessible by admin, best_pal, and go_getter roles.
    """
    caller_id = _require_chat_id(x_telegram_chat_id)
    async with AsyncSessionLocal() as db:
        await require_role(db, caller_id, [Role.admin, Role.best_pal, Role.go_getter])
        from app.crud.tracks import get_subcategories

        subs = await get_subcategories(db, category_id=category_id)
        return [
            {
                "id": sub.id,
                "category_id": sub.category_id,
                "name": sub.name,
                "description": sub.description,
            }
            for sub in subs
        ]
