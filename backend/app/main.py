"""Main FastAPI application for Lucid."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routes import (
    projects,
    templates,
    stage1,
    stage_style,
    stage2,
    stage3,
    stage4,
    export,
    fonts,
    config,
    prompts,
)
from app.services.gemini_service import GeminiError
from app.services.llm_logger import start_flow, _flow_name_from_path

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise the database and seed defaults on startup."""
    from app.db.database import init_db
    from app.dependencies import container

    try:
        await init_db()
        await container.template_manager.seed_defaults()
        await container.project_manager.load_all()
        logger.info("Database initialised successfully")
    except Exception as e:
        logger.error(f"Database initialisation failed: {e}", exc_info=True)

    yield


app = FastAPI(
    title="Lucid API",
    description="Transform rough drafts into polished social-media carousels",
    version="0.2.0",
    lifespan=lifespan,
)

# Configure CORS for frontend
cors_origins = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:5173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(templates.router, prefix="/api/templates", tags=["templates"])
app.include_router(stage1.router, prefix="/api/stage1", tags=["stage1"])
app.include_router(stage_style.router, prefix="/api/stage-style", tags=["stage-style"])
app.include_router(stage2.router, prefix="/api/stage2", tags=["stage2"])
app.include_router(stage3.router, prefix="/api/stage3", tags=["stage3"])
app.include_router(stage4.router, prefix="/api/stage4", tags=["stage4"])
app.include_router(export.router, prefix="/api/export", tags=["export"])
app.include_router(fonts.router, prefix="/api/fonts", tags=["fonts"])
app.include_router(config.router, prefix="/api/config", tags=["config"])
app.include_router(prompts.router, prefix="/api/prompts", tags=["prompts"])


@app.middleware("http")
async def llm_log_flow(request: Request, call_next):
    """Assign a per-request log flow so all LLM calls land in one file."""
    start_flow(_flow_name_from_path(request.url.path))
    return await call_next(request)


@app.exception_handler(GeminiError)
async def gemini_error_handler(request: Request, exc: GeminiError):
    """Return a clear error when Gemini AI is unavailable or fails."""
    return JSONResponse(
        status_code=503,
        content={"detail": str(exc)},
    )


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Lucid API is running"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
