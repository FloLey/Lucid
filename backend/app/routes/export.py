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


_VALID_FORMATS = {"png", "jpeg", "webp"}
_FORMAT_MIME = {"png": "image/png", "jpeg": "image/jpeg", "webp": "image/webp"}


def _normalise_format(fmt: str) -> str:
    """Return a valid image format key, defaulting to 'png'."""
    return fmt.lower() if fmt.lower() in _VALID_FORMATS else "png"


async def _build_zip_response(
    project_id: str, export_service: ExportService, fmt: str = "png"
) -> StreamingResponse:
    """Build a ZIP streaming response for a project."""
    zip_buffer = await export_service.export_project(project_id, fmt)
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
    project_id: str, slide_index: int, export_service: ExportService, fmt: str = "png"
) -> StreamingResponse:
    """Build an image streaming response for a single slide."""
    image_buffer = await export_service.export_single_slide(project_id, slide_index, fmt)
    if not image_buffer:
        raise HTTPException(status_code=404, detail="Slide not found or no image")

    ext = "jpg" if fmt == "jpeg" else fmt
    filename = f"slide_{slide_index + 1:02d}.{ext}"
    return StreamingResponse(
        image_buffer,
        media_type=_FORMAT_MIME.get(fmt, "image/png"),
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
    project_id: str,
    format: str = "png",
    export_service: ExportService = Depends(get_export_service),
):
    """Export all slides as a ZIP archive (GET method for direct download).

    Supports ``?format=png`` (default), ``jpeg``, or ``webp``.
    """
    return await _build_zip_response(project_id, export_service, _normalise_format(format))


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
    format: str = "png",
    export_service: ExportService = Depends(get_export_service),
):
    """Export a single slide (GET method for direct download).

    Supports ``?format=png`` (default), ``jpeg``, or ``webp``.
    """
    return await _build_slide_response(
        project_id, slide_index, export_service, _normalise_format(format)
    )
