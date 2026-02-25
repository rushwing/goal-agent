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


async def require_best_pal_or_admin(
    chat_id: Annotated[Optional[int], Depends(get_chat_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> int:
    if chat_id is None:
        raise HTTPException(status_code=401, detail="X-Telegram-Chat-Id header required")
    role = await resolve_role(db, chat_id)
    if role not in (Role.admin, Role.best_pal):
        raise HTTPException(status_code=403, detail="Best pal or admin role required")
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


async def verify_best_pal_owns_go_getter(
    go_getter_id: int,
    chat_id: int,
    db: AsyncSession,
) -> None:
    """Raise 403 if the authenticated best_pal doesn't own the given go_getter. Admin always passes."""
    role = await resolve_role(db, chat_id)
    if role == Role.admin:
        return
    from app.crud.go_getters import crud_go_getter
    from app.crud.best_pals import crud_best_pal

    best_pal = await crud_best_pal.get_by_chat_id(db, chat_id)
    if not best_pal:
        raise HTTPException(status_code=403, detail="Best pal not found")
    go_getter = await crud_go_getter.get(db, go_getter_id)
    if not go_getter or go_getter.best_pal_id != best_pal.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this go getter")
