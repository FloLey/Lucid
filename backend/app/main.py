"""Main FastAPI application for Lucid."""

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routes import sessions, stage1, stage_style, stage2, stage3, stage4, chat, export, fonts
from app.services.gemini_service import GeminiError

app = FastAPI(
    title="Lucid API",
    description="Transform rough drafts into polished social-media carousels",
    version="0.1.0",
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
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(stage1.router, prefix="/api/stage1", tags=["stage1"])
app.include_router(stage_style.router, prefix="/api/stage-style", tags=["stage-style"])
app.include_router(stage2.router, prefix="/api/stage2", tags=["stage2"])
app.include_router(stage3.router, prefix="/api/stage3", tags=["stage3"])
app.include_router(stage4.router, prefix="/api/stage4", tags=["stage4"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(export.router, prefix="/api/export", tags=["export"])
app.include_router(fonts.router, prefix="/api/fonts", tags=["fonts"])


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
