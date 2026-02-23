"""FastAPI dependencies."""
from typing import Annotated, Optional
from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.mcp.auth import resolve_role, Role, AuthError


async def get_chat_id(x_telegram_chat_id: Annotated[Optional[int], Header()] = None) -> Optional[int]:
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
