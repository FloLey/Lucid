"""Chat interface routes with SSE streaming."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.chat_service import chat_service, cancel_agent
from app.services.session_manager import session_manager

router = APIRouter()


class ChatMessageRequest(BaseModel):
    """Request to send a chat message."""

    session_id: str
    message: str = Field(min_length=1, description="User message or command")


class ChatResponse(BaseModel):
    """Response from chat processing."""

    success: bool
    response: str
    tool_called: str | None = None
    session: dict | None = None


class CancelRequest(BaseModel):
    """Request to cancel an in-progress agent loop."""

    session_id: str


class UndoRequest(BaseModel):
    """Request to undo the last agent's write operations."""

    session_id: str


@router.post("/message")
async def send_message(request: ChatMessageRequest):
    """Process a chat message via streaming agent loop (SSE)."""
    return StreamingResponse(
        chat_service.process_message_stream(
            session_id=request.session_id,
            message=request.message,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/cancel")
async def cancel(request: CancelRequest):
    """Signal the agent loop to stop after the current step."""
    cancel_agent(request.session_id)
    return {"status": "cancelled"}


@router.post("/undo")
async def undo(request: UndoRequest):
    """Restore session to pre-agent snapshot."""
    snapshot = session_manager.get_snapshot(request.session_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="No snapshot available to undo")

    session = session_manager.restore_snapshot(request.session_id)
    return {"session": session.model_dump(mode="json")}


@router.get("/commands")
async def list_commands():
    """List available slash commands."""
    commands = {
        "/next": "Advance to the next stage",
        "/back": "Go to the previous stage",
        "/stage <1-5>": "Go to a specific stage",
        "/regen slide <n>": "Regenerate text for slide n",
        "/regen prompt <n>": "Regenerate image prompt for slide n",
        "/regen image <n>": "Regenerate background image for slide n",
        "/generate": "Run the main generation for the current stage",
        "/export": "Export carousel as ZIP",
    }
    return {"commands": commands}


@router.get("/placeholder")
async def placeholder():
    """Placeholder endpoint for backwards compatibility."""
    return {"feature": "chat", "status": "active"}
