"""Aggregates all v1 routers."""

from fastapi import APIRouter
from app.api.v1.admin import router as admin_router
from app.api.v1.plans import router as plans_router
from app.api.v1.checkins import router as checkins_router
from app.api.v1.reports import router as reports_router
from app.api.v1.tracks import router as tracks_router
from app.api.v1.goal_groups import router as goal_groups_router
from app.api.v1.wizards import router as wizards_router

router = APIRouter()
router.include_router(admin_router)
router.include_router(plans_router)
router.include_router(checkins_router)
router.include_router(reports_router)
router.include_router(tracks_router)
router.include_router(goal_groups_router)
router.include_router(wizards_router)
