"""Stage 1 routes - Draft to Slide texts."""

from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.models.project import ProjectResponse
from app.dependencies import get_stage1_service
from app.services.stage1_service import Stage1Service
from app.routes.utils import execute_service_action

router = APIRouter()


class GenerateSlideTextsRequest(BaseModel):
    """Request to generate slide texts from a draft."""

    project_id: str
    draft_text: str = Field(min_length=1, description="The draft text to transform")
    num_slides: Optional[int] = Field(default=None, ge=1, le=20)
    include_titles: bool = Field(default=True)
    additional_instructions: Optional[str] = None
    language: str = Field(default="English")


class RegenerateSlideTextRequest(BaseModel):
    """Request to regenerate a single slide text."""

    project_id: str
    slide_index: int = Field(ge=0)
    instruction: Optional[str] = None


class UpdateSlideTextRequest(BaseModel):
    """Request to update a slide's text."""

    project_id: str
    slide_index: int = Field(ge=0)
    title: Optional[str] = None
    body: Optional[str] = None


class RegenerateAllRequest(BaseModel):
    """Request to regenerate all slide texts."""

    project_id: str


@router.post("/generate", response_model=ProjectResponse)
async def generate_slide_texts(
    request: GenerateSlideTextsRequest,
    stage1_service: Stage1Service = Depends(get_stage1_service),
):
    """Generate slide texts from a draft."""
    return await execute_service_action(
        lambda: stage1_service.generate_slide_texts(
            project_id=request.project_id,
            draft_text=request.draft_text,
            num_slides=request.num_slides,
            include_titles=request.include_titles,
            additional_instructions=request.additional_instructions,
            language=request.language,
        ),
        "Failed to generate slide texts",
    )


@router.post("/regenerate-all", response_model=ProjectResponse)
async def regenerate_all_slide_texts(
    request: RegenerateAllRequest,
    stage1_service: Stage1Service = Depends(get_stage1_service),
):
    """Regenerate all slide texts."""
    return await execute_service_action(
        lambda: stage1_service.regenerate_all_slide_texts(
            project_id=request.project_id,
        ),
        "Failed to regenerate slides",
    )


@router.post("/regenerate", response_model=ProjectResponse)
async def regenerate_slide_text(
    request: RegenerateSlideTextRequest,
    stage1_service: Stage1Service = Depends(get_stage1_service),
):
    """Regenerate a single slide text."""
    return await execute_service_action(
        lambda: stage1_service.regenerate_slide_text(
            project_id=request.project_id,
            slide_index=request.slide_index,
            instruction=request.instruction,
        ),
        "Failed to regenerate slide",
    )


@router.post("/update", response_model=ProjectResponse)
async def update_slide_text(
    request: UpdateSlideTextRequest,
    stage1_service: Stage1Service = Depends(get_stage1_service),
):
    """Manually update a slide's text."""
    return await execute_service_action(
        lambda: stage1_service.update_slide_text(
            project_id=request.project_id,
            slide_index=request.slide_index,
            title=request.title,
            body=request.body,
        ),
        "Project or slide not found",
    )


@router.get("/placeholder")
def placeholder():
    """Placeholder endpoint for backwards compatibility."""
    return {"stage": 1, "status": "active"}
