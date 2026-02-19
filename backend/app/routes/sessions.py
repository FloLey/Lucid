"""Session management routes."""

from fastapi import APIRouter, HTTPException, Depends

from app.models.session import (
    CreateSessionRequest,
    StageAdvanceRequest,
    SessionResponse,
)
from app.dependencies import get_session_manager
from app.services.session_manager import SessionManager

router = APIRouter()


@router.get("/")
def list_sessions(session_manager: SessionManager = Depends(get_session_manager)):
    """List all active sessions (for debugging)."""
    return {"sessions": list(session_manager.sessions.keys())}


@router.post("/create", response_model=SessionResponse)
async def create_session(
    request: CreateSessionRequest,
    session_manager: SessionManager = Depends(get_session_manager),
):
    """Create a new session or return existing one."""
    session = await session_manager.create_session(request.session_id)
    if not session:
        raise HTTPException(status_code=500, detail="Failed to create session")
    return {"session": session.model_dump()}


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager),
):
    """Get a session by ID."""
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": session.model_dump()}


@router.delete("/{session_id}")
async def delete_session(
    session_id: str, session_manager: SessionManager = Depends(get_session_manager)
):
    """Delete a session."""
    if await session_manager.delete_session(session_id):
        return {"deleted": True}
    raise HTTPException(status_code=404, detail="Session not found")


@router.post("/next-stage", response_model=SessionResponse)
async def next_stage(
    request: StageAdvanceRequest,
    session_manager: SessionManager = Depends(get_session_manager),
):
    """Advance to the next stage."""
    session = await session_manager.advance_stage(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": session.model_dump()}


@router.post("/previous-stage", response_model=SessionResponse)
async def previous_stage(
    request: StageAdvanceRequest,
    session_manager: SessionManager = Depends(get_session_manager),
):
    """Go back to the previous stage."""
    session = await session_manager.previous_stage(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": session.model_dump()}


@router.post("/{session_id}/stage/{stage}", response_model=SessionResponse)
async def go_to_stage(
    session_id: str,
    stage: int,
    session_manager: SessionManager = Depends(get_session_manager),
):
    """Go to a specific stage."""
    if not 1 <= stage <= 5:
        raise HTTPException(status_code=400, detail="Stage must be between 1 and 5")

    session = await session_manager.go_to_stage(session_id, stage)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": session.model_dump()}
