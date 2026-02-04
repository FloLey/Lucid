"""Main FastAPI application for Lucid."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import sessions, stage1, stage2, stage3, stage4, chat, export, fonts

app = FastAPI(
    title="Lucid API",
    description="Transform rough drafts into polished social-media carousels",
    version="0.1.0",
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(stage1.router, prefix="/api/stage1", tags=["stage1"])
app.include_router(stage2.router, prefix="/api/stage2", tags=["stage2"])
app.include_router(stage3.router, prefix="/api/stage3", tags=["stage3"])
app.include_router(stage4.router, prefix="/api/stage4", tags=["stage4"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(export.router, prefix="/api/export", tags=["export"])
app.include_router(fonts.router, prefix="/api/fonts", tags=["fonts"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Lucid API is running"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
