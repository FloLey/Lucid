"""Project management routes — /api/projects."""

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import (
    get_project_manager,
    get_storage_service,
    get_template_manager,
    get_config_manager,
    get_prompt_loader,
    get_stage_draft_service,
)
from app.models.project import (
    MAX_STAGES,
    CreateProjectRequest,
    ProjectConfig,
    ProjectListResponse,
    ProjectResponse,
    RenameProjectRequest,
)
from app.services.config_manager import ConfigManager
from app.services.project_manager import ProjectManager
from app.services.prompt_loader import PromptLoader
from app.services.stage_draft_service import StageDraftService
from app.services.storage_service import StorageService
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
    config_manager: ConfigManager = Depends(get_config_manager),
    prompt_loader: PromptLoader = Depends(get_prompt_loader),
):
    """Create a new project, optionally from a template."""
    slide_count = 5  # default when no template
    if request.template_id:
        template = await template_manager.get_template(request.template_id)
        if template is None:
            raise HTTPException(status_code=404, detail="Template not found")
        project_config = template.config
        slide_count = template.default_slide_count
    else:
        # Seed blank projects with global config + current prompts so they
        # inherit defaults instead of using hard-coded Pydantic field defaults.
        app_config = config_manager.get_config()
        prompts = prompt_loader.load_all()
        project_config = ProjectConfig.from_app_config(app_config, prompts)

    project = await project_manager.create_project(
        slide_count=slide_count,
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
    storage_service: StorageService = Depends(get_storage_service),
):
    """Delete a project and its associated image files."""
    deleted = await project_manager.delete_project(project_id, storage_service=storage_service)
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
    if not 1 <= stage <= MAX_STAGES:
        raise HTTPException(status_code=400, detail=f"Stage must be between 1 and {MAX_STAGES}")
    project = await project_manager.go_to_stage(project_id, stage)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project": project}


@router.post("/{project_id}/generate-title", response_model=ProjectResponse)
async def generate_title(
    project_id: str,
    stage_draft_service: StageDraftService = Depends(get_stage_draft_service),
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Generate a descriptive project title using AI based on slide content."""
    project = await stage_draft_service.generate_project_title(project_id, force=True)
    if not project:
        # Return current project state even if title generation was skipped
        project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project": project}
