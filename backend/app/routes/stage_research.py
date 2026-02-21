"""Stage Research routes — grounded chat and draft extraction."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.models.project import ProjectResponse
from app.dependencies import get_stage_research_service
from app.services.gemini_service import GeminiError
from app.services.stage_research_service import StageResearchService
from app.routes.utils import execute_service_action

logger = logging.getLogger(__name__)
router = APIRouter()


class ResearchChatRequest(BaseModel):
    """Request body for the chat endpoint."""

    project_id: str
    message: str = Field(min_length=1, description="User message to send to the AI")


class ExtractDraftRequest(BaseModel):
    """Request body for the extract-draft endpoint."""

    project_id: str
    research_instructions: Optional[str] = Field(
        default=None,
        description="Instructions for how to summarise the conversation into a draft",
    )


@router.post("/chat", response_model=ProjectResponse)
async def research_chat(
    request: ResearchChatRequest,
    stage_research_service: StageResearchService = Depends(get_stage_research_service),
):
    """Send a user message and receive a search-grounded AI reply."""
    try:
        project = await stage_research_service.send_message(
            project_id=request.project_id,
            message=request.message,
        )
    except GeminiError:
        raise
    except Exception as e:
        logger.error("Research chat failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Research chat failed")
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project": project.model_dump()}


@router.post("/extract-draft", response_model=ProjectResponse)
async def extract_draft(
    request: ExtractDraftRequest,
    stage_research_service: StageResearchService = Depends(get_stage_research_service),
):
    """Summarise the research conversation into a draft and advance to Stage Draft."""
    return await execute_service_action(
        lambda: stage_research_service.extract_draft(
            project_id=request.project_id,
            research_instructions=request.research_instructions,
        ),
        "Failed to extract draft from research",
    )
