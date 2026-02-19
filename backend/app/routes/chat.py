"""Chat route with Server-Sent Events streaming."""

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()


class ChatMessageRequest(BaseModel):
    """Request model for a user chat message."""

    project_id: str
    message: str


@router.post("/message")
async def chat_message(request: ChatMessageRequest):
    """Process a chat message and stream responses via SSE."""

    async def event_stream():
        """Generator for Server-Sent Events."""
        yield f"data: {json.dumps({'type': 'status', 'message': 'Chat received'})}\n\n"
        yield f"data: {json.dumps({'type': 'text', 'content': f'Echo: {request.message}'})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
