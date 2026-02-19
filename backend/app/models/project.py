"""Project and Template Pydantic models."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.slide import Slide
from app.models.style_proposal import StyleProposal
from app.models.config import (
    AppConfig,
    GlobalDefaultsConfig,
    ImageConfig,
    StageInstructionsConfig,
    StyleConfig,
)


# ---------------------------------------------------------------------------
# Project configuration (AppConfig + per-project prompt texts)
# ---------------------------------------------------------------------------


class ProjectConfig(BaseModel):
    """Configuration deep-copied from a Template at project creation time.

    Extends AppConfig with embedded prompt templates so each project is
    self-contained and independent of global `.prompt` files.
    """

    stage_instructions: StageInstructionsConfig = Field(
        default_factory=StageInstructionsConfig
    )
    global_defaults: GlobalDefaultsConfig = Field(default_factory=GlobalDefaultsConfig)
    image: ImageConfig = Field(default_factory=ImageConfig)
    style: StyleConfig = Field(default_factory=StyleConfig)

    # Prompt templates stored inline (prompt_file_stem -> content).
    # e.g. {"slide_generation": "...", "style_proposal": "...", ...}
    prompts: Dict[str, str] = Field(default_factory=dict)

    @classmethod
    def from_app_config(
        cls, app_config: AppConfig, prompts: Dict[str, str]
    ) -> "ProjectConfig":
        """Build a ProjectConfig from an AppConfig + prompt dict."""
        return cls(
            stage_instructions=app_config.stage_instructions.model_copy(deep=True),
            global_defaults=app_config.global_defaults.model_copy(deep=True),
            image=app_config.image.model_copy(deep=True),
            style=app_config.style.model_copy(deep=True),
            prompts=dict(prompts),
        )

    def get_prompt(self, name: str) -> Optional[str]:
        """Return the prompt text for *name* (without .prompt suffix)."""
        return self.prompts.get(name)


# ---------------------------------------------------------------------------
# Core project state (the full pipeline state blob)
# ---------------------------------------------------------------------------


class ProjectState(BaseModel):
    """Complete project state — stored in the ``state`` JSON column."""

    project_id: str = Field(description="Unique project identifier (UUID)")
    name: str = Field(default="Untitled Project")
    mode: str = Field(default="carousel", description="carousel or single_image")
    slide_count: int = Field(default=5, ge=1, le=20)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Stage tracking
    current_stage: int = Field(default=1, ge=1, le=5)

    # Per-project configuration (deep copy from chosen template)
    project_config: ProjectConfig = Field(default_factory=ProjectConfig)

    # Stage 1 inputs
    draft_text: str = Field(default="", description="Original draft text")
    num_slides: Optional[int] = Field(default=None, ge=1, le=20)
    include_titles: bool = Field(default=True)
    additional_instructions: Optional[str] = Field(default=None)
    language: str = Field(default="English")

    # Stage Style data
    style_proposals: List[StyleProposal] = Field(default_factory=list)
    selected_style_proposal_index: Optional[int] = Field(default=None)

    # Stage 2 inputs
    image_style_instructions: Optional[str] = Field(default=None)
    shared_prompt_prefix: Optional[str] = Field(default=None)

    # Slides data (populated through stages)
    slides: List[Slide] = Field(default_factory=list)

    # Thumbnail (auto-set after Stage Style proposals are generated)
    thumbnail_b64: Optional[str] = Field(default=None)

    def update_timestamp(self) -> None:
        """Refresh the updated_at timestamp."""
        self.updated_at = datetime.utcnow()

    def get_slide(self, index: int) -> Optional[Slide]:
        """Return slide at *index*, or None if out of range."""
        if 0 <= index < len(self.slides):
            return self.slides[index]
        return None

    def ensure_slides(self, count: int) -> None:
        """Ensure at least *count* slides exist."""
        while len(self.slides) < count:
            self.slides.append(Slide(index=len(self.slides)))


# ---------------------------------------------------------------------------
# Lightweight card (for listing projects)
# ---------------------------------------------------------------------------


class ProjectCard(BaseModel):
    """Minimal project representation for the project-list endpoint."""

    project_id: str
    name: str
    mode: str
    current_stage: int
    slide_count: int
    thumbnail_b64: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class CreateProjectRequest(BaseModel):
    """Request body for POST /api/projects."""

    mode: str = Field(default="carousel", pattern=r"^(carousel|single_image)$")
    slide_count: int = Field(default=5, ge=1, le=20)
    template_id: Optional[str] = Field(default=None)


class RenameProjectRequest(BaseModel):
    """Request body for PATCH /api/projects/{id}/name."""

    name: str = Field(min_length=1, max_length=200)


class ProjectResponse(BaseModel):
    """Response wrapping a full ProjectState."""

    project: ProjectState


class ProjectListResponse(BaseModel):
    """Response wrapping a list of ProjectCards."""

    projects: List[ProjectCard]


# ---------------------------------------------------------------------------
# Template models
# ---------------------------------------------------------------------------


class TemplateData(BaseModel):
    """Full template data (returned from API)."""

    id: str
    name: str
    default_mode: str
    default_slide_count: int
    config: ProjectConfig
    created_at: datetime


class CreateTemplateRequest(BaseModel):
    """Request body for POST /api/templates."""

    name: str = Field(min_length=1, max_length=200)
    default_mode: str = Field(default="carousel", pattern=r"^(carousel|single_image)$")
    default_slide_count: int = Field(default=5, ge=1, le=20)
    config: Optional[ProjectConfig] = None


class UpdateTemplateRequest(BaseModel):
    """Request body for PATCH /api/templates/{id}."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    default_mode: Optional[str] = Field(
        default=None, pattern=r"^(carousel|single_image)$"
    )
    default_slide_count: Optional[int] = Field(default=None, ge=1, le=20)
    config: Optional[ProjectConfig] = None


class TemplateListResponse(BaseModel):
    """Response wrapping a list of templates."""

    templates: List[TemplateData]
