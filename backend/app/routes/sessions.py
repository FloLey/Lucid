"""Session management routes."""

from fastapi import APIRouter, HTTPException

from app.services.session_manager import session_manager
from app.models.session import CreateSessionRequest, StageAdvanceRequest

router = APIRouter()


@router.get("/")
async def list_sessions():
    """List all active sessions (for debugging)."""
    return {"sessions": list(session_manager.sessions.keys())}


@router.post("/create")
async def create_session(request: CreateSessionRequest):
    """Create a new session or return existing one."""
    session = session_manager.create_session(request.session_id)
    return {"session": session.model_dump()}


@router.get("/{session_id}")
async def get_session(session_id: str):
    """Get a session by ID."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": session.model_dump()}


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    if session_manager.delete_session(session_id):
        return {"deleted": True}
    raise HTTPException(status_code=404, detail="Session not found")


@router.post("/next-stage")
async def next_stage(request: StageAdvanceRequest):
    """Advance to the next stage."""
    session = session_manager.advance_stage(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": session.model_dump()}


@router.post("/previous-stage")
async def previous_stage(request: StageAdvanceRequest):
    """Go back to the previous stage."""
    session = session_manager.previous_stage(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": session.model_dump()}


@router.post("/{session_id}/stage/{stage}")
async def go_to_stage(session_id: str, stage: int):
    """Go to a specific stage."""
    if not 1 <= stage <= 4:
        raise HTTPException(status_code=400, detail="Stage must be between 1 and 4")

    session = session_manager.go_to_stage(session_id, stage)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": session.model_dump()}
