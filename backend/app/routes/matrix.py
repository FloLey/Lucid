"""API routes for the Concept Matrix Generator."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.models.matrix import (
    CreateMatrixRequest,
    MatrixListResponse,
    MatrixProjectResponse,
    MatrixSettingsResponse,
    RegenerateCellRequest,
    UpdateMatrixSettingsRequest,
)
from app.dependencies import (
    get_matrix_db,
    get_matrix_service,
    get_matrix_settings_manager,
)
from app.services.matrix_db import MatrixDB
from app.services.matrix_service import MatrixService
from app.services.matrix_settings_manager import MatrixSettingsManager

logger = logging.getLogger(__name__)

router = APIRouter()
settings_router = APIRouter()


# ── Projects ──────────────────────────────────────────────────────────────


@router.get("/", response_model=MatrixListResponse)
async def list_matrices(
    db: MatrixDB = Depends(get_matrix_db),
) -> MatrixListResponse:
    cards = await db.list_projects()
    return MatrixListResponse(matrices=cards)


@router.post("/", response_model=MatrixProjectResponse)
async def create_matrix(
    req: CreateMatrixRequest,
    service: MatrixService = Depends(get_matrix_service),
) -> MatrixProjectResponse:
    """Create a matrix project and launch background generation."""
    if req.n > 8:
        raise HTTPException(status_code=400, detail="n must be ≤ 8")
    project = await service.create_and_start(req)
    return MatrixProjectResponse(matrix=project)


@router.get("/{project_id}", response_model=MatrixProjectResponse)
async def get_matrix(
    project_id: str,
    db: MatrixDB = Depends(get_matrix_db),
) -> MatrixProjectResponse:
    project = await db.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Matrix not found")
    return MatrixProjectResponse(matrix=project)


@router.delete("/{project_id}")
async def delete_matrix(
    project_id: str,
    service: MatrixService = Depends(get_matrix_service),
    db: MatrixDB = Depends(get_matrix_db),
) -> dict:
    if service.is_generating(project_id):
        await service.cancel_generation(project_id)
    deleted = await db.delete_project(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Matrix not found")
    return {"deleted": True}


@router.post("/{project_id}/cancel")
async def cancel_matrix(
    project_id: str,
    service: MatrixService = Depends(get_matrix_service),
) -> dict:
    if not service.is_generating(project_id):
        raise HTTPException(status_code=400, detail="Not currently generating")
    await service.cancel_generation(project_id)
    return {"cancelled": True}


@router.post("/{project_id}/generate-images")
async def generate_images(
    project_id: str,
    service: MatrixService = Depends(get_matrix_service),
    db: MatrixDB = Depends(get_matrix_db),
) -> dict:
    """Trigger image generation for all cells of an existing matrix."""
    project = await db.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Matrix not found")
    if service.is_generating(project_id):
        raise HTTPException(status_code=400, detail="Generation already in progress")
    # Run in background
    import asyncio
    asyncio.create_task(service.generate_images_for_project(project_id))
    return {"started": True}


@router.post("/{project_id}/cells/{row}/{col}/regenerate")
async def regenerate_cell(
    project_id: str,
    row: int,
    col: int,
    req: RegenerateCellRequest,
    service: MatrixService = Depends(get_matrix_service),
    db: MatrixDB = Depends(get_matrix_db),
) -> MatrixProjectResponse:
    project = await db.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Matrix not found")
    if row == col:
        raise HTTPException(
            status_code=400, detail="Use /diagonal/{k}/regenerate for diagonal cells"
        )
    await service.regenerate_cell(
        project_id=project_id,
        row=row,
        col=col,
        extra_instructions=req.extra_instructions or "",
        image_only=req.image_only,
    )
    updated = await db.get_project(project_id)
    if updated is None:
        raise HTTPException(status_code=500, detail="Failed to fetch regenerated matrix")
    return MatrixProjectResponse(matrix=updated)


# ── SSE Stream ────────────────────────────────────────────────────────────


@router.get("/{project_id}/stream")
async def stream_matrix(
    project_id: str,
    service: MatrixService = Depends(get_matrix_service),
) -> StreamingResponse:
    """Server-Sent Events stream for live generation updates."""

    async def event_generator():
        async for event in service.subscribe(project_id):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ── Settings (mounted at /api/matrix-settings) ────────────────────────────


@settings_router.get("/", response_model=MatrixSettingsResponse)
async def get_matrix_settings(
    mgr: MatrixSettingsManager = Depends(get_matrix_settings_manager),
) -> MatrixSettingsResponse:
    return MatrixSettingsResponse(settings=mgr.get())


@settings_router.put("/", response_model=MatrixSettingsResponse)
async def update_matrix_settings(
    req: UpdateMatrixSettingsRequest,
    mgr: MatrixSettingsManager = Depends(get_matrix_settings_manager),
    service: MatrixService = Depends(get_matrix_service),
) -> MatrixSettingsResponse:
    updated = mgr.update(req.settings)
    service.load_settings(updated)
    return MatrixSettingsResponse(settings=updated)


@settings_router.post("/reset", response_model=MatrixSettingsResponse)
async def reset_matrix_settings(
    mgr: MatrixSettingsManager = Depends(get_matrix_settings_manager),
    service: MatrixService = Depends(get_matrix_service),
) -> MatrixSettingsResponse:
    reset = mgr.reset()
    service.load_settings(reset)
    return MatrixSettingsResponse(settings=reset)
