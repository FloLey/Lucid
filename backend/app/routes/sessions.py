"""Session management routes."""

from fastapi import APIRouter, HTTPException

from app.services.session_manager import session_manager
from app.models.session import CreateSessionRequest, StageAdvanceRequest
from app.routes.dependencies import get_session_or_404

router = APIRouter()


@router.get("/")
def list_sessions():
    """List all active sessions (for debugging)."""
    return {"sessions": list(session_manager.sessions.keys())}


@router.post("/create")
def create_session(request: CreateSessionRequest):
    """Create a new session or return existing one."""
    session = session_manager.create_session(request.session_id)
    return {"session": session.model_dump()}


@router.get("/{session_id}")
def get_session(session_id: str):
    """Get a session by ID."""
    session = get_session_or_404(session_id)
    return {"session": session.model_dump()}


@router.delete("/{session_id}")
def delete_session(session_id: str):
    """Delete a session."""
    if session_manager.delete_session(session_id):
        return {"deleted": True}
    raise HTTPException(status_code=404, detail="Session not found")


@router.post("/next-stage")
def next_stage(request: StageAdvanceRequest):
    """Advance to the next stage."""
    get_session_or_404(request.session_id)
    session = session_manager.advance_stage(request.session_id)
    return {"session": session.model_dump()}


@router.post("/previous-stage")
def previous_stage(request: StageAdvanceRequest):
    """Go back to the previous stage."""
    get_session_or_404(request.session_id)
    session = session_manager.previous_stage(request.session_id)
    return {"session": session.model_dump()}


@router.post("/{session_id}/stage/{stage}")
def go_to_stage(session_id: str, stage: int):
    """Go to a specific stage."""
    if not 1 <= stage <= 5:
        raise HTTPException(status_code=400, detail="Stage must be between 1 and 5")

    get_session_or_404(session_id)
    session = session_manager.go_to_stage(session_id, stage)
    return {"session": session.model_dump()}
