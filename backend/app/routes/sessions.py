"""Session management routes."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_sessions():
    """List all active sessions (for debugging)."""
    from app.services.session_manager import session_manager
    return {"sessions": list(session_manager.sessions.keys())}
