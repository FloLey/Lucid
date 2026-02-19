"""Stage 3 routes - Image prompts to Images."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.models.project import ProjectResponse
from app.dependencies import get_stage3_service
from app.services.stage3_service import Stage3Service
from app.routes.utils import execute_service_action

router = APIRouter()


class GenerateImagesRequest(BaseModel):
    """Request to generate images for all slides."""

    project_id: str


class RegenerateImageRequest(BaseModel):
    """Request to regenerate a single image."""

    project_id: str
    slide_index: int = Field(ge=0)


class SetImageRequest(BaseModel):
    """Request to set image data directly."""

    project_id: str
    slide_index: int = Field(ge=0)
    image_data: str = Field(min_length=1, description="Base64 encoded image data")


@router.post("/generate", response_model=ProjectResponse)
async def generate_all_images(
    request: GenerateImagesRequest,
    stage3_service: Stage3Service = Depends(get_stage3_service),
):
    """Generate images for all slides."""
    return await execute_service_action(
        lambda: stage3_service.generate_all_images(
            project_id=request.project_id,
        ),
        "Failed to generate images",
    )


@router.post("/regenerate", response_model=ProjectResponse)
async def regenerate_image(
    request: RegenerateImageRequest,
    stage3_service: Stage3Service = Depends(get_stage3_service),
):
    """Regenerate image for a single slide."""
    return await execute_service_action(
        lambda: stage3_service.regenerate_image(
            project_id=request.project_id,
            slide_index=request.slide_index,
        ),
        "Failed to regenerate image",
    )


@router.post("/upload", response_model=ProjectResponse)
async def set_image(
    request: SetImageRequest,
    stage3_service: Stage3Service = Depends(get_stage3_service),
):
    """Set image data directly (for custom uploads)."""
    return await execute_service_action(
        lambda: stage3_service.set_image_data(
            project_id=request.project_id,
            slide_index=request.slide_index,
            image_data=request.image_data,
        ),
        "Project or slide not found",
    )


@router.get("/placeholder")
async def placeholder():
    """Placeholder endpoint for backwards compatibility."""
    return {"stage": 3, "status": "active"}
