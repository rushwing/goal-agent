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


async def verify_best_pal_owns_go_getter(
    db: AsyncSession, caller_id: int, go_getter_id: int
) -> None:
    """Raise PermissionError/ValueError if the caller doesn't own the go_getter.

    Admins always pass. Best pals must be the assigned best_pal for the go_getter.
    """
    role = await resolve_role(db, caller_id)
    if role == Role.admin:
        return

    go_getter = await crud_go_getter.get(db, go_getter_id)
    if not go_getter:
        raise ValueError("Go getter not found")

    best_pal = await crud_best_pal.get_by_chat_id(db, caller_id)
    if best_pal is None or go_getter.best_pal_id != best_pal.id:
        raise PermissionError("Not authorized to access this go getter")
