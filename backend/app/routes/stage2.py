"""Stage 2 routes - Slide texts to Image prompts."""

from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.models.project import ProjectResponse
from app.dependencies import get_stage2_service
from app.services.stage2_service import Stage2Service
from app.routes.utils import execute_service_action

router = APIRouter()


class GeneratePromptsRequest(BaseModel):
    """Request to generate image prompts."""

    project_id: str
    image_style_instructions: Optional[str] = Field(
        default=None,
        description="Style instructions for image generation (mood, palette, style)",
    )


class RegeneratePromptRequest(BaseModel):
    """Request to regenerate a single prompt."""

    project_id: str
    slide_index: int = Field(ge=0)


class UpdatePromptRequest(BaseModel):
    """Request to update a prompt."""

    project_id: str
    slide_index: int = Field(ge=0)
    prompt: str = Field(min_length=1)


class UpdateStyleRequest(BaseModel):
    """Request to update style instructions."""

    project_id: str
    style_instructions: str


@router.post("/generate", response_model=ProjectResponse)
async def generate_all_prompts(
    request: GeneratePromptsRequest,
    stage2_service: Stage2Service = Depends(get_stage2_service),
):
    """Generate image prompts for all slides."""
    return await execute_service_action(
        lambda: stage2_service.generate_all_prompts(
            project_id=request.project_id,
            image_style_instructions=request.image_style_instructions,
        ),
        "Failed to generate prompts",
    )


@router.post("/regenerate", response_model=ProjectResponse)
async def regenerate_prompt(
    request: RegeneratePromptRequest,
    stage2_service: Stage2Service = Depends(get_stage2_service),
):
    """Regenerate image prompt for a single slide."""
    return await execute_service_action(
        lambda: stage2_service.regenerate_prompt(
            project_id=request.project_id,
            slide_index=request.slide_index,
        ),
        "Failed to regenerate prompt",
    )


@router.post("/update", response_model=ProjectResponse)
async def update_prompt(
    request: UpdatePromptRequest,
    stage2_service: Stage2Service = Depends(get_stage2_service),
):
    """Manually update an image prompt."""
    return await execute_service_action(
        lambda: stage2_service.update_prompt(
            project_id=request.project_id,
            slide_index=request.slide_index,
            prompt=request.prompt,
        ),
        "Project or slide not found",
    )


@router.post("/style", response_model=ProjectResponse)
async def update_style(
    request: UpdateStyleRequest,
    stage2_service: Stage2Service = Depends(get_stage2_service),
):
    """Update the shared style instructions."""
    return await execute_service_action(
        lambda: stage2_service.update_style_instructions(
            project_id=request.project_id,
            style_instructions=request.style_instructions,
        ),
        "Project not found",
    )
