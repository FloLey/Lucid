"""Stage Style routes - Visual style proposal generation and selection."""

from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.models.session import SessionResponse
from app.dependencies import get_stage_style_service
from app.services.stage_style_service import StageStyleService
from app.routes.utils import execute_service_action

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
async def generate_proposals(
    request: GenerateProposalsRequest,
    stage_style_service: StageStyleService = Depends(get_stage_style_service),
):
    """Generate style proposals with preview images."""
    return await execute_service_action(
        lambda: stage_style_service.generate_proposals(
            session_id=request.session_id,
            num_proposals=request.num_proposals,
            additional_instructions=request.additional_instructions,
        ),
        "Failed to generate style proposals",
    )


@router.post("/select", response_model=SessionResponse)
async def select_proposal(
    request: SelectProposalRequest,
    stage_style_service: StageStyleService = Depends(get_stage_style_service),
):
    """Select a style proposal."""
    return await execute_service_action(
        lambda: stage_style_service.select_proposal(
            session_id=request.session_id,
            proposal_index=request.proposal_index,
        ),
        "Session not found or invalid proposal index",
    )


@router.get("/placeholder")
def placeholder():
    """Placeholder endpoint for backwards compatibility."""
    return {"stage": "style", "status": "active"}
