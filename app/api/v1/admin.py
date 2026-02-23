"""Admin endpoints: pupils and parents management."""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.v1.deps import require_admin
from app.crud import crud_pupil, crud_parent
from app.schemas.pupil import PupilCreate, PupilUpdate, PupilResponse
from app.schemas.parent import ParentCreate, ParentUpdate, ParentResponse

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/pupils", response_model=list[PupilResponse])
async def list_pupils(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[int, Depends(require_admin)],
):
    return await crud_pupil.get_multi(db)


@router.post("/pupils", response_model=PupilResponse, status_code=201)
async def create_pupil(
    body: PupilCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[int, Depends(require_admin)],
):
    return await crud_pupil.create(db, obj_in=body)


@router.patch("/pupils/{pupil_id}", response_model=PupilResponse)
async def update_pupil(
    pupil_id: int,
    body: PupilUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[int, Depends(require_admin)],
):
    pupil = await crud_pupil.get(db, pupil_id)
    if not pupil:
        raise HTTPException(404, "Pupil not found")
    return await crud_pupil.update(db, db_obj=pupil, obj_in=body)


@router.delete("/pupils/{pupil_id}")
async def delete_pupil(
    pupil_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[int, Depends(require_admin)],
):
    pupil = await crud_pupil.get(db, pupil_id)
    if not pupil:
        raise HTTPException(404, "Pupil not found")
    pupil.is_active = False
    await db.flush()
    return {"success": True}


@router.get("/parents", response_model=list[ParentResponse])
async def list_parents(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[int, Depends(require_admin)],
):
    return await crud_parent.get_multi(db)


@router.post("/parents", response_model=ParentResponse, status_code=201)
async def create_parent(
    body: ParentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[int, Depends(require_admin)],
):
    return await crud_parent.create(db, obj_in=body)


@router.patch("/parents/{parent_id}", response_model=ParentResponse)
async def update_parent(
    parent_id: int,
    body: ParentUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[int, Depends(require_admin)],
):
    parent = await crud_parent.get(db, parent_id)
    if not parent:
        raise HTTPException(404, "Parent not found")
    return await crud_parent.update(db, db_obj=parent, obj_in=body)


@router.delete("/parents/{parent_id}")
async def delete_parent(
    parent_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[int, Depends(require_admin)],
):
    parent = await crud_parent.remove(db, id=parent_id)
    if not parent:
        raise HTTPException(404, "Parent not found")
    return {"success": True}
