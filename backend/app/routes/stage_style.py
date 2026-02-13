"""Stage Style routes - Visual style proposal generation and selection."""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.stage_style_service import stage_style_service
from app.services.gemini_service import GeminiError
from app.models.session import SessionResponse

logger = logging.getLogger(__name__)

router = APIRouter()


class GenerateProposalsRequest(BaseModel):
    """Request to generate style proposals."""

    session_id: str
    num_proposals: int = Field(default=3, ge=1, le=5)
    additional_instructions: Optional[str] = None


class SelectProposalRequest(BaseModel):
    """Request to select a style proposal."""

    session_id: str
    proposal_index: int = Field(ge=0)


@router.post("/generate", response_model=SessionResponse)
async def generate_proposals(request: GenerateProposalsRequest):
    """Generate style proposals with preview images."""
    try:
        session = await stage_style_service.generate_proposals(
            session_id=request.session_id,
            num_proposals=request.num_proposals,
            additional_instructions=request.additional_instructions,
        )
    except GeminiError:
        raise
    except Exception as e:
        logger.error(f"Failed to generate style proposals: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate style proposals: {e}")
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or no slides")
    return {"session": session.model_dump()}


@router.post("/select", response_model=SessionResponse)
def select_proposal(request: SelectProposalRequest):
    """Select a style proposal."""
    session = stage_style_service.select_proposal(
        session_id=request.session_id,
        proposal_index=request.proposal_index,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or invalid proposal index")
    return {"session": session.model_dump()}


@router.get("/placeholder")
def placeholder():
    """Placeholder endpoint for backwards compatibility."""
    return {"stage": "style", "status": "active"}
