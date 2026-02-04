"""Export routes."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.export_service import export_service

router = APIRouter()


class ExportRequest(BaseModel):
    """Request to export a session."""

    session_id: str


class ExportSlideRequest(BaseModel):
    """Request to export a single slide."""

    session_id: str
    slide_index: int = Field(ge=0)


@router.post("/zip")
async def export_zip(request: ExportRequest):
    """Export all slides as a ZIP archive."""
    zip_buffer = export_service.export_session(request.session_id)
    if not zip_buffer:
        raise HTTPException(status_code=404, detail="Session not found or no slides")

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=lucid_carousel_{request.session_id}.zip"
        },
    )


@router.get("/zip/{session_id}")
async def export_zip_get(session_id: str):
    """Export all slides as a ZIP archive (GET method for direct download)."""
    zip_buffer = export_service.export_session(session_id)
    if not zip_buffer:
        raise HTTPException(status_code=404, detail="Session not found or no slides")

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=lucid_carousel_{session_id}.zip"
        },
    )


@router.post("/slide")
async def export_slide(request: ExportSlideRequest):
    """Export a single slide as PNG."""
    image_buffer = export_service.export_single_slide(
        request.session_id,
        request.slide_index,
    )
    if not image_buffer:
        raise HTTPException(status_code=404, detail="Slide not found or no image")

    filename = f"slide_{request.slide_index + 1:02d}.png"
    return StreamingResponse(
        image_buffer,
        media_type="image/png",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        },
    )


@router.get("/slide/{session_id}/{slide_index}")
async def export_slide_get(session_id: str, slide_index: int):
    """Export a single slide as PNG (GET method for direct download)."""
    image_buffer = export_service.export_single_slide(session_id, slide_index)
    if not image_buffer:
        raise HTTPException(status_code=404, detail="Slide not found or no image")

    filename = f"slide_{slide_index + 1:02d}.png"
    return StreamingResponse(
        image_buffer,
        media_type="image/png",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        },
    )


@router.get("/placeholder")
async def placeholder():
    """Placeholder endpoint for backwards compatibility."""
    return {"feature": "export", "status": "active"}
