"""Main FastAPI application for Lucid."""

import logging
import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.routes import (
    projects,
    templates,
    stage_research,
    stage_draft,
    stage_style,
    stage_prompts,
    stage_images,
    stage_typography,
    export,
    fonts,
    config,
    prompts,
    matrix,
)
from app.services.gemini_service import GeminiError
from app.services.storage_service import IMAGE_DIR
from app.services.llm_logger import start_flow, _flow_name_from_path

logger = logging.getLogger(__name__)


class _RateLimiter:
    """In-memory sliding-window rate limiter (per IP)."""

    def __init__(self, max_calls: int, window_seconds: float) -> None:
        self._max = max_calls
        self._window = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self._window
        hits = self._hits[key]
        hits[:] = [t for t in hits if t > cutoff]
        if len(hits) >= self._max:
            return False
        hits.append(now)
        return True


_limiter = _RateLimiter(max_calls=120, window_seconds=60.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise the database and seed defaults on startup."""
    from app.db.database import init_db
    from app.dependencies import container

    try:
        await init_db()
        await container.template_manager.seed_defaults()
        # Ensure the image storage directory exists on disk
        IMAGE_DIR.mkdir(parents=True, exist_ok=True)
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
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Include routers
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(templates.router, prefix="/api/templates", tags=["templates"])
app.include_router(stage_research.router, prefix="/api/stage-research", tags=["stage-research"])
app.include_router(stage_draft.router, prefix="/api/stage-draft", tags=["stage-draft"])
app.include_router(stage_style.router, prefix="/api/stage-style", tags=["stage-style"])
app.include_router(stage_prompts.router, prefix="/api/stage-prompts", tags=["stage-prompts"])
app.include_router(stage_images.router, prefix="/api/stage-images", tags=["stage-images"])
app.include_router(stage_typography.router, prefix="/api/stage-typography", tags=["stage-typography"])
app.include_router(export.router, prefix="/api/export", tags=["export"])
app.include_router(fonts.router, prefix="/api/fonts", tags=["fonts"])
app.include_router(config.router, prefix="/api/config", tags=["config"])
app.include_router(prompts.router, prefix="/api/prompts", tags=["prompts"])
app.include_router(matrix.router, prefix="/api/matrix", tags=["matrix"])
app.include_router(matrix.settings_router, prefix="/api/matrix-settings", tags=["matrix-settings"])

# Serve generated images directly so the frontend can load them via
# /images/<uuid>.png without going through the API layer.
app.mount("/images", StaticFiles(directory=str(IMAGE_DIR)), name="images")


@app.middleware("http")
async def llm_log_flow(request: Request, call_next):
    """Assign a per-request log flow so all LLM calls land in one file."""
    start_flow(_flow_name_from_path(request.url.path))
    return await call_next(request)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Reject /api requests that exceed 120 per minute per IP."""
    if request.url.path.startswith("/api/"):
        client_ip = request.client.host if request.client else "unknown"
        if not _limiter.is_allowed(client_ip):
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please slow down."},
                headers={"Retry-After": "60"},
            )
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
