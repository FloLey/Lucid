"""Stage 4 routes - Typography/Layout rendering."""

from typing import Dict, Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.models.session import SessionResponse
from app.dependencies import get_stage4_service
from app.services.stage4_service import Stage4Service
from app.routes.utils import execute_service_action

router = APIRouter()


class ApplyTextRequest(BaseModel):
    """Request to apply text to images."""

    session_id: str
    use_ai_suggestions: bool = Field(default=True)


class ApplyTextSingleRequest(BaseModel):
    """Request to apply text to a single image."""

    session_id: str
    slide_index: int = Field(ge=0)


class SuggestStyleRequest(BaseModel):
    """Request to get AI style suggestions."""

    session_id: str
    slide_index: int = Field(ge=0)


class UpdateStyleRequest(BaseModel):
    """Request to update style properties."""

    session_id: str
    slide_index: int = Field(ge=0)
    style: Dict[str, Any] = Field(description="Style properties to update")


class ApplyStyleAllRequest(BaseModel):
    """Request to apply style to all slides."""

    session_id: str
    style: Dict[str, Any] = Field(description="Style properties to apply")


@router.post("/apply-all", response_model=SessionResponse)
async def apply_text_to_all(
    request: ApplyTextRequest,
    stage4_service: Stage4Service = Depends(get_stage4_service),
):
    """Apply text styling to all slide images."""
    return await execute_service_action(
        lambda: stage4_service.apply_text_to_all_images(
            session_id=request.session_id,
            use_ai_suggestions=request.use_ai_suggestions,
        ),
        "Failed to apply text to images",
    )


@router.post("/apply", response_model=SessionResponse)
async def apply_text_to_image(
    request: ApplyTextSingleRequest,
    stage4_service: Stage4Service = Depends(get_stage4_service),
):
    """Apply text styling to a single slide image."""
    return await execute_service_action(
        lambda: stage4_service.apply_text_to_image(
            session_id=request.session_id,
            slide_index=request.slide_index,
        ),
        "Failed to apply text to image",
    )


@router.post("/suggest", response_model=SessionResponse)
async def suggest_style(
    request: SuggestStyleRequest,
    stage4_service: Stage4Service = Depends(get_stage4_service),
):
    """Get AI suggestions for text styling."""
    return await execute_service_action(
        lambda: stage4_service.suggest_style(
            session_id=request.session_id,
            slide_index=request.slide_index,
        ),
        "Failed to suggest style",
    )


@router.post("/update-style", response_model=SessionResponse)
async def update_style(
    request: UpdateStyleRequest,
    stage4_service: Stage4Service = Depends(get_stage4_service),
):
    """Update style properties for a slide."""
    return await execute_service_action(
        lambda: stage4_service.update_style(
            session_id=request.session_id,
            slide_index=request.slide_index,
            style_updates=request.style,
        ),
        "Session or slide not found",
    )


@router.post("/apply-style-all", response_model=SessionResponse)
async def apply_style_to_all(
    request: ApplyStyleAllRequest,
    stage4_service: Stage4Service = Depends(get_stage4_service),
):
    """Apply style updates to all slides."""
    return await execute_service_action(
        lambda: stage4_service.apply_style_to_all(
            session_id=request.session_id,
            style_updates=request.style,
        ),
        "Session not found or no slides",
    )


@router.get("/placeholder")
async def placeholder():
    """Placeholder endpoint for backwards compatibility."""
    return {"stage": 4, "status": "active"}
