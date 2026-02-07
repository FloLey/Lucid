"""Stage 2 routes - Slide texts to Image prompts."""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.stage2_service import stage2_service

router = APIRouter()


class GeneratePromptsRequest(BaseModel):
    """Request to generate image prompts."""

    session_id: str
    image_style_instructions: Optional[str] = Field(
        default=None,
        description="Style instructions for image generation (mood, palette, style)",
    )


class RegeneratePromptRequest(BaseModel):
    """Request to regenerate a single prompt."""

    session_id: str
    slide_index: int = Field(ge=0)


class UpdatePromptRequest(BaseModel):
    """Request to update a prompt."""

    session_id: str
    slide_index: int = Field(ge=0)
    prompt: str = Field(min_length=1)


class UpdateStyleRequest(BaseModel):
    """Request to update style instructions."""

    session_id: str
    style_instructions: str


@router.post("/generate")
async def generate_all_prompts(request: GeneratePromptsRequest):
    """Generate image prompts for all slides."""
    session = await stage2_service.generate_all_prompts(
        session_id=request.session_id,
        image_style_instructions=request.image_style_instructions,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or no slides")
    return {"session": session.model_dump()}


@router.post("/regenerate")
async def regenerate_prompt(request: RegeneratePromptRequest):
    """Regenerate image prompt for a single slide."""
    session = await stage2_service.regenerate_prompt(
        session_id=request.session_id,
        slide_index=request.slide_index,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session or slide not found")
    return {"session": session.model_dump()}


@router.post("/update")
async def update_prompt(request: UpdatePromptRequest):
    """Manually update an image prompt."""
    session = stage2_service.update_prompt(
        session_id=request.session_id,
        slide_index=request.slide_index,
        prompt=request.prompt,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session or slide not found")
    return {"session": session.model_dump()}


@router.post("/style")
async def update_style(request: UpdateStyleRequest):
    """Update the shared style instructions."""
    session = stage2_service.update_style_instructions(
        session_id=request.session_id,
        style_instructions=request.style_instructions,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": session.model_dump()}


@router.get("/placeholder")
async def placeholder():
    """Placeholder endpoint for backwards compatibility."""
    return {"stage": 2, "status": "active"}
