"""Project management routes — /api/projects."""

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_project_manager, get_template_manager
from app.models.project import (
    CreateProjectRequest,
    ProjectListResponse,
    ProjectResponse,
    RenameProjectRequest,
    StageNavigationRequest,
)
from app.services.project_manager import ProjectManager
from app.services.template_manager import TemplateManager

router = APIRouter()


@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Return lightweight cards for all projects (sorted newest-first)."""
    cards = await project_manager.list_projects()
    return {"projects": cards}


@router.post("/", response_model=ProjectResponse)
async def create_project(
    request: CreateProjectRequest,
    project_manager: ProjectManager = Depends(get_project_manager),
    template_manager: TemplateManager = Depends(get_template_manager),
):
    """Create a new project, optionally from a template."""
    project_config = None
    if request.template_id:
        project_config = await template_manager.get_template_config(request.template_id)
        if project_config is None:
            raise HTTPException(status_code=404, detail="Template not found")

    project = await project_manager.create_project(
        mode=request.mode,
        slide_count=request.slide_count,
        project_config=project_config,
    )
    return {"project": project}


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Return the full project state."""
    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project": project}


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Delete a project."""
    deleted = await project_manager.delete_project(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"deleted": True}


@router.patch("/{project_id}/name", response_model=ProjectResponse)
async def rename_project(
    project_id: str,
    request: RenameProjectRequest,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Rename a project."""
    project = await project_manager.rename_project(project_id, request.name)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project": project}


@router.post("/{project_id}/next-stage", response_model=ProjectResponse)
async def next_stage(
    project_id: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Advance to the next stage."""
    project = await project_manager.advance_stage(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project": project}


@router.post("/{project_id}/prev-stage", response_model=ProjectResponse)
async def prev_stage(
    project_id: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Return to the previous stage."""
    project = await project_manager.previous_stage(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project": project}


@router.post("/{project_id}/goto-stage/{stage}", response_model=ProjectResponse)
async def goto_stage(
    project_id: str,
    stage: int,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Jump to a specific stage."""
    if not 1 <= stage <= 5:
        raise HTTPException(status_code=400, detail="Stage must be between 1 and 5")
    project = await project_manager.go_to_stage(project_id, stage)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project": project}
