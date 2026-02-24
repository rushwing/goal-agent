"""MCP role-based auth: resolves X-Telegram-Chat-Id to admin/parent/pupil."""

import logging
from enum import Enum
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import crud_parent, crud_pupil

logger = logging.getLogger(__name__)


class Role(str, Enum):
    admin = "admin"
    parent = "parent"
    pupil = "pupil"
    unknown = "unknown"


async def resolve_role(db: AsyncSession, chat_id: int) -> Role:
    """Determine role from telegram_chat_id."""
    parent = await crud_parent.get_by_chat_id(db, chat_id)
    if parent:
        return Role.admin if parent.is_admin else Role.parent

    pupil = await crud_pupil.get_by_chat_id(db, chat_id)
    if pupil:
        return Role.pupil

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
