"""Stage 3 routes - Image prompts to Images."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.stage3_service import stage3_service

router = APIRouter()


class GenerateImagesRequest(BaseModel):
    """Request to generate images for all slides."""

    session_id: str


class RegenerateImageRequest(BaseModel):
    """Request to regenerate a single image."""

    session_id: str
    slide_index: int = Field(ge=0)


class SetImageRequest(BaseModel):
    """Request to set image data directly."""

    session_id: str
    slide_index: int = Field(ge=0)
    image_data: str = Field(min_length=1, description="Base64 encoded image data")


@router.post("/generate")
async def generate_all_images(request: GenerateImagesRequest):
    """Generate images for all slides."""
    session = await stage3_service.generate_all_images(
        session_id=request.session_id,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or no slides")
    return {"session": session.model_dump()}


@router.post("/regenerate")
async def regenerate_image(request: RegenerateImageRequest):
    """Regenerate image for a single slide."""
    session = await stage3_service.regenerate_image(
        session_id=request.session_id,
        slide_index=request.slide_index,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session or slide not found")
    return {"session": session.model_dump()}


@router.post("/upload")
async def set_image(request: SetImageRequest):
    """Set image data directly (for custom uploads)."""
    session = stage3_service.set_image_data(
        session_id=request.session_id,
        slide_index=request.slide_index,
        image_data=request.image_data,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session or slide not found")
    return {"session": session.model_dump()}


@router.get("/placeholder")
async def placeholder():
    """Placeholder endpoint for backwards compatibility."""
    return {"stage": 3, "status": "active"}
