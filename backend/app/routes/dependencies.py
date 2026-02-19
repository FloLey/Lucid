"""Shared FastAPI dependencies for route handlers."""

from fastapi import HTTPException, Depends

from app.models.session import SessionState
from app.dependencies import get_session_manager
from app.services.session_manager import SessionManager


async def get_session_or_404(
    session_id: str, session_manager: SessionManager = Depends(get_session_manager)
) -> SessionState:
    """Retrieve a session by ID or raise HTTP 404."""
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
