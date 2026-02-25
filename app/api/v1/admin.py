"""Admin endpoints: go_getters and best_pals management."""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.v1.deps import require_admin
from app.crud import crud_go_getter, crud_best_pal
from app.schemas.go_getter import GoGetterCreate, GoGetterUpdate, GoGetterResponse
from app.schemas.best_pal import BestPalCreate, BestPalUpdate, BestPalResponse

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/go_getters", response_model=list[GoGetterResponse])
async def list_go_getters(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[int, Depends(require_admin)],
):
    return await crud_go_getter.get_multi(db)


@router.post("/go_getters", response_model=GoGetterResponse, status_code=201)
async def create_go_getter(
    body: GoGetterCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[int, Depends(require_admin)],
):
    return await crud_go_getter.create(db, obj_in=body)


@router.patch("/go_getters/{go_getter_id}", response_model=GoGetterResponse)
async def update_go_getter(
    go_getter_id: int,
    body: GoGetterUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[int, Depends(require_admin)],
):
    go_getter = await crud_go_getter.get(db, go_getter_id)
    if not go_getter:
        raise HTTPException(404, "Go getter not found")
    return await crud_go_getter.update(db, db_obj=go_getter, obj_in=body)


@router.delete("/go_getters/{go_getter_id}")
async def delete_go_getter(
    go_getter_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[int, Depends(require_admin)],
):
    go_getter = await crud_go_getter.get(db, go_getter_id)
    if not go_getter:
        raise HTTPException(404, "Go getter not found")
    go_getter.is_active = False
    await db.flush()
    return {"success": True}


@router.get("/best_pals", response_model=list[BestPalResponse])
async def list_best_pals(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[int, Depends(require_admin)],
):
    return await crud_best_pal.get_multi(db)


@router.post("/best_pals", response_model=BestPalResponse, status_code=201)
async def create_best_pal(
    body: BestPalCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[int, Depends(require_admin)],
):
    return await crud_best_pal.create(db, obj_in=body)


@router.patch("/best_pals/{best_pal_id}", response_model=BestPalResponse)
async def update_best_pal(
    best_pal_id: int,
    body: BestPalUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[int, Depends(require_admin)],
):
    best_pal = await crud_best_pal.get(db, best_pal_id)
    if not best_pal:
        raise HTTPException(404, "Best pal not found")
    return await crud_best_pal.update(db, db_obj=best_pal, obj_in=body)


@router.delete("/best_pals/{best_pal_id}")
async def delete_best_pal(
    best_pal_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[int, Depends(require_admin)],
):
    best_pal = await crud_best_pal.remove(db, id=best_pal_id)
    if not best_pal:
        raise HTTPException(404, "Best pal not found")
    return {"success": True}
