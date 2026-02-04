"""Stage 1 routes - Draft to Slide texts."""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.stage1_service import stage1_service

router = APIRouter()


class GenerateSlideTextsRequest(BaseModel):
    """Request to generate slide texts from a draft."""

    session_id: str
    draft_text: str = Field(min_length=1, description="The draft text to transform")
    num_slides: int = Field(default=5, ge=1, le=20)
    include_titles: bool = Field(default=True)
    additional_instructions: Optional[str] = None


class RegenerateSlideTextRequest(BaseModel):
    """Request to regenerate a single slide text."""

    session_id: str
    slide_index: int = Field(ge=0)


class UpdateSlideTextRequest(BaseModel):
    """Request to update a slide's text."""

    session_id: str
    slide_index: int = Field(ge=0)
    title: Optional[str] = None
    body: Optional[str] = None


class RegenerateAllRequest(BaseModel):
    """Request to regenerate all slide texts."""

    session_id: str


@router.post("/generate")
async def generate_slide_texts(request: GenerateSlideTextsRequest):
    """Generate slide texts from a draft."""
    session = await stage1_service.generate_slide_texts(
        session_id=request.session_id,
        draft_text=request.draft_text,
        num_slides=request.num_slides,
        include_titles=request.include_titles,
        additional_instructions=request.additional_instructions,
    )
    if not session:
        raise HTTPException(status_code=500, detail="Failed to generate slide texts")
    return {"session": session.model_dump()}


@router.post("/regenerate-all")
async def regenerate_all_slide_texts(request: RegenerateAllRequest):
    """Regenerate all slide texts."""
    session = await stage1_service.regenerate_all_slide_texts(
        session_id=request.session_id,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or no draft")
    return {"session": session.model_dump()}


@router.post("/regenerate")
async def regenerate_slide_text(request: RegenerateSlideTextRequest):
    """Regenerate a single slide text."""
    session = await stage1_service.regenerate_slide_text(
        session_id=request.session_id,
        slide_index=request.slide_index,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session or slide not found")
    return {"session": session.model_dump()}


@router.post("/update")
async def update_slide_text(request: UpdateSlideTextRequest):
    """Manually update a slide's text."""
    session = stage1_service.update_slide_text(
        session_id=request.session_id,
        slide_index=request.slide_index,
        title=request.title,
        body=request.body,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session or slide not found")
    return {"session": session.model_dump()}


@router.get("/placeholder")
async def placeholder():
    """Placeholder endpoint for backwards compatibility."""
    return {"stage": 1, "status": "active"}
