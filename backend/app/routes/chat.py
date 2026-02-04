"""Chat interface routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.chat_service import chat_service

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


@router.post("/message")
async def send_message(request: ChatMessageRequest) -> ChatResponse:
    """Process a chat message and execute any commands."""
    result = await chat_service.process_message(
        session_id=request.session_id,
        message=request.message,
    )
    return ChatResponse(**result)


@router.get("/commands")
async def list_commands():
    """List available slash commands."""
    commands = {
        "/next": "Advance to the next stage",
        "/stage <1-4>": "Go to a specific stage",
        "/regen slide <n>": "Regenerate text for slide n",
        "/regen prompt <n>": "Regenerate image prompt for slide n",
        "/regen image <n>": "Regenerate background image for slide n",
        "/apply preset <name>": "Apply a style preset (modern, bold, elegant, minimal, impact)",
    }
    return {"commands": commands}


@router.get("/placeholder")
async def placeholder():
    """Placeholder endpoint for backwards compatibility."""
    return {"feature": "chat", "status": "active"}
