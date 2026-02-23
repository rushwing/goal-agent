"""FastAPI application entry point with FastMCP mounted and APScheduler."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.services.scheduler_service import scheduler, setup_scheduler

logger = logging.getLogger(__name__)
settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.APP_DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Vacation Study Planner...")
    setup_scheduler()
    scheduler.start()
    logger.info("APScheduler started with %d jobs", len(scheduler.get_jobs()))
    yield
    # Shutdown
    scheduler.shutdown(wait=False)
    logger.info("APScheduler stopped")


app = FastAPI(
    title="Vacation Study Planner",
    description="AI-powered vacation study planner for families",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST API router
from app.api.v1.router import router as api_router  # noqa: E402

app.include_router(api_router, prefix="/api/v1")

# FastMCP ASGI sub-app
from app.mcp.server import mcp  # noqa: E402

mcp_app = mcp.http_app(path="/mcp")
app.mount("/mcp", mcp_app)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "vacation-study-planner"}
