"""Shared FastAPI dependencies for route handlers."""

from fastapi import HTTPException

from app.models.session import SessionState
from app.services.session_manager import session_manager


def get_session_or_404(session_id: str) -> SessionState:
    """Retrieve a session by ID or raise HTTP 404."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
