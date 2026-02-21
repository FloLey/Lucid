"""Stage Typography routes - Typography/Layout rendering."""

from typing import Dict, Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.models.project import ProjectResponse
from app.dependencies import get_stage_typography_service
from app.services.stage_typography_service import StageTypographyService
from app.routes.utils import execute_service_action

router = APIRouter()


class ApplyTextRequest(BaseModel):
    """Request to apply text to images."""

    project_id: str
    use_ai_suggestions: bool = Field(default=True)


class ApplyTextSingleRequest(BaseModel):
    """Request to apply text to a single image."""

    project_id: str
    slide_index: int = Field(ge=0)


class SuggestStyleRequest(BaseModel):
    """Request to get AI style suggestions."""

    project_id: str
    slide_index: int = Field(ge=0)


class UpdateStyleRequest(BaseModel):
    """Request to update style properties."""

    project_id: str
    slide_index: int = Field(ge=0)
    style: Dict[str, Any] = Field(description="Style properties to update")


class ApplyStyleAllRequest(BaseModel):
    """Request to apply style to all slides."""

    project_id: str
    style: Dict[str, Any] = Field(description="Style properties to apply")


@router.post("/apply-all", response_model=ProjectResponse)
async def apply_text_to_all(
    request: ApplyTextRequest,
    stage_typography_service: StageTypographyService = Depends(get_stage_typography_service),
):
    """Apply text styling to all slide images."""
    return await execute_service_action(
        lambda: stage_typography_service.apply_text_to_all_images(
            project_id=request.project_id,
            use_ai_suggestions=request.use_ai_suggestions,
        ),
        "Failed to apply text to images",
    )


@router.post("/apply", response_model=ProjectResponse)
async def apply_text_to_image(
    request: ApplyTextSingleRequest,
    stage_typography_service: StageTypographyService = Depends(get_stage_typography_service),
):
    """Apply text styling to a single slide image."""
    return await execute_service_action(
        lambda: stage_typography_service.apply_text_to_image(
            project_id=request.project_id,
            slide_index=request.slide_index,
        ),
        "Failed to apply text to image",
    )


@router.post("/suggest", response_model=ProjectResponse)
async def suggest_style(
    request: SuggestStyleRequest,
    stage_typography_service: StageTypographyService = Depends(get_stage_typography_service),
):
    """Get AI suggestions for text styling."""
    return await execute_service_action(
        lambda: stage_typography_service.suggest_style(
            project_id=request.project_id,
            slide_index=request.slide_index,
        ),
        "Failed to suggest style",
    )


@router.post("/update-style", response_model=ProjectResponse)
async def update_style(
    request: UpdateStyleRequest,
    stage_typography_service: StageTypographyService = Depends(get_stage_typography_service),
):
    """Update style properties for a slide."""
    return await execute_service_action(
        lambda: stage_typography_service.update_style(
            project_id=request.project_id,
            slide_index=request.slide_index,
            style_updates=request.style,
        ),
        "Project or slide not found",
    )


@router.post("/apply-style-all", response_model=ProjectResponse)
async def apply_style_to_all(
    request: ApplyStyleAllRequest,
    stage_typography_service: StageTypographyService = Depends(get_stage_typography_service),
):
    """Apply style updates to all slides."""
    return await execute_service_action(
        lambda: stage_typography_service.apply_style_to_all(
            project_id=request.project_id,
            style_updates=request.style,
        ),
        "Project not found or no slides",
    )
