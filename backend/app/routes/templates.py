"""Template management routes — /api/templates."""

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_template_manager
from app.models.project import (
    CreateTemplateRequest,
    TemplateData,
    TemplateListResponse,
    UpdateTemplateRequest,
)
from app.services.template_manager import TemplateManager

router = APIRouter()


@router.get("/", response_model=TemplateListResponse)
async def list_templates(
    template_manager: TemplateManager = Depends(get_template_manager),
):
    """Return all templates."""
    templates = await template_manager.list_templates()
    return {"templates": templates}


@router.post("/", response_model=TemplateData)
async def create_template(
    request: CreateTemplateRequest,
    template_manager: TemplateManager = Depends(get_template_manager),
):
    """Create a new template."""
    template = await template_manager.create_template(
        name=request.name,
        default_slide_count=request.default_slide_count,
        config=request.config,
    )
    return template


@router.get("/{template_id}", response_model=TemplateData)
async def get_template(
    template_id: str,
    template_manager: TemplateManager = Depends(get_template_manager),
):
    """Return a single template by ID."""
    template = await template_manager.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.patch("/{template_id}", response_model=TemplateData)
async def update_template(
    template_id: str,
    request: UpdateTemplateRequest,
    template_manager: TemplateManager = Depends(get_template_manager),
):
    """Update a template's fields."""
    template = await template_manager.update_template(
        template_id=template_id,
        name=request.name,
        default_slide_count=request.default_slide_count,
        config=request.config,
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    template_manager: TemplateManager = Depends(get_template_manager),
):
    """Delete a template."""
    deleted = await template_manager.delete_template(template_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"deleted": True}
