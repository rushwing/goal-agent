"""FastAPI dependencies."""

from typing import Annotated, Optional
from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.mcp.auth import resolve_role, Role, AuthError


async def get_chat_id(
    x_telegram_chat_id: Annotated[Optional[int], Header()] = None,
) -> Optional[int]:
    return x_telegram_chat_id


async def require_admin(
    chat_id: Annotated[Optional[int], Depends(get_chat_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> int:
    if chat_id is None:
        raise HTTPException(status_code=401, detail="X-Telegram-Chat-Id header required")
    role = await resolve_role(db, chat_id)
    if role != Role.admin:
        raise HTTPException(status_code=403, detail="Admin role required")
    return chat_id


async def require_parent_or_admin(
    chat_id: Annotated[Optional[int], Depends(get_chat_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> int:
    if chat_id is None:
        raise HTTPException(status_code=401, detail="X-Telegram-Chat-Id header required")
    role = await resolve_role(db, chat_id)
    if role not in (Role.admin, Role.parent):
        raise HTTPException(status_code=403, detail="Parent or admin role required")
    return chat_id


async def require_any_role(
    chat_id: Annotated[Optional[int], Depends(get_chat_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> int:
    if chat_id is None:
        raise HTTPException(status_code=401, detail="X-Telegram-Chat-Id header required")
    role = await resolve_role(db, chat_id)
    if role == Role.unknown:
        raise HTTPException(status_code=403, detail="Unknown user")
    return chat_id


async def verify_parent_owns_pupil(
    pupil_id: int,
    chat_id: int,
    db: AsyncSession,
) -> None:
    """Raise 403 if the authenticated parent doesn't own the given pupil. Admin always passes."""
    role = await resolve_role(db, chat_id)
    if role == Role.admin:
        return
    from app.crud.pupils import crud_pupil
    from app.crud.parents import crud_parent

    parent = await crud_parent.get_by_chat_id(db, chat_id)
    if not parent:
        raise HTTPException(status_code=403, detail="Parent not found")
    pupil = await crud_pupil.get(db, pupil_id)
    if not pupil or pupil.parent_id != parent.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this pupil")
