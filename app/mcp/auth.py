"""MCP role-based auth: resolves X-Telegram-Chat-Id to admin/best_pal/go_getter."""

import logging
from enum import Enum
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import crud_best_pal, crud_go_getter

logger = logging.getLogger(__name__)


class Role(str, Enum):
    admin = "admin"
    best_pal = "best_pal"
    go_getter = "go_getter"
    unknown = "unknown"


async def resolve_role(db: AsyncSession, chat_id: int) -> Role:
    """Determine role from telegram_chat_id."""
    best_pal = await crud_best_pal.get_by_chat_id(db, chat_id)
    if best_pal:
        return Role.admin if best_pal.is_admin else Role.best_pal

    go_getter = await crud_go_getter.get_by_chat_id(db, chat_id)
    if go_getter:
        return Role.go_getter

    return Role.unknown


class AuthError(Exception):
    pass


async def require_role(
    db: AsyncSession,
    chat_id: int,
    allowed_roles: list[Role],
) -> Role:
    """Resolve role and raise AuthError if not in allowed_roles."""
    role = await resolve_role(db, chat_id)
    if role not in allowed_roles:
        raise AuthError(
            f"Access denied. Required roles: {[r.value for r in allowed_roles]}, "
            f"your role: {role.value}"
        )
    return role
