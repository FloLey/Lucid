"""Export routes."""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.dependencies import get_export_service
from app.services.export_service import ExportService

router = APIRouter()


class ExportRequest(BaseModel):
    """Request to export a project."""

    project_id: str


class ExportSlideRequest(BaseModel):
    """Request to export a single slide."""

    project_id: str
    slide_index: int = Field(ge=0)


async def _build_zip_response(
    project_id: str, export_service: ExportService
) -> StreamingResponse:
    """Build a ZIP streaming response for a project."""
    zip_buffer = await export_service.export_project(project_id)
    if not zip_buffer:
        raise HTTPException(status_code=404, detail="Project not found or no slides")

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=lucid_carousel_{project_id}.zip"
        },
    )


async def _build_slide_response(
    project_id: str, slide_index: int, export_service: ExportService
) -> StreamingResponse:
    """Build a PNG streaming response for a single slide."""
    image_buffer = await export_service.export_single_slide(project_id, slide_index)
    if not image_buffer:
        raise HTTPException(status_code=404, detail="Slide not found or no image")

    filename = f"slide_{slide_index + 1:02d}.png"
    return StreamingResponse(
        image_buffer,
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/zip")
async def export_zip(
    request: ExportRequest, export_service: ExportService = Depends(get_export_service)
):
    """Export all slides as a ZIP archive."""
    return await _build_zip_response(request.project_id, export_service)


@router.get("/zip/{project_id}")
async def export_zip_get(
    project_id: str, export_service: ExportService = Depends(get_export_service)
):
    """Export all slides as a ZIP archive (GET method for direct download)."""
    return await _build_zip_response(project_id, export_service)


@router.post("/slide")
async def export_slide(
    request: ExportSlideRequest,
    export_service: ExportService = Depends(get_export_service),
):
    """Export a single slide as PNG."""
    return await _build_slide_response(
        request.project_id, request.slide_index, export_service
    )


@router.get("/slide/{project_id}/{slide_index}")
async def export_slide_get(
    project_id: str,
    slide_index: int,
    export_service: ExportService = Depends(get_export_service),
):
    """Export a single slide as PNG (GET method for direct download)."""
    return await _build_slide_response(project_id, slide_index, export_service)
