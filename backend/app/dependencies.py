"""Dependency injection container for Lucid services."""

from app.services.project_manager import (
    ProjectManager,
    project_manager as _project_manager,
)
from app.services.template_manager import (
    TemplateManager,
    template_manager as _template_manager,
)
from app.services.gemini_service import GeminiService
from app.services.image_service import ImageService
from app.services.storage_service import StorageService
from app.services.stage_research_service import StageResearchService
from app.services.stage_draft_service import StageDraftService
from app.services.stage_style_service import StageStyleService
from app.services.stage_prompts_service import StagePromptsService
from app.services.stage_images_service import StageImagesService
from app.services.stage_typography_service import StageTypographyService
from app.services.rendering_service import RenderingService
from app.services.export_service import ExportService
from app.services.config_manager import ConfigManager
from app.services.prompt_validator import PromptValidator
from app.services.font_manager import FontManager
from app.services.prompt_loader import PromptLoader


class ServiceContainer:
    """Container for managing service instances."""

    def __init__(self):
        # Core services
        self.project_manager = _project_manager
        self.template_manager = _template_manager
        self.config_manager = ConfigManager()
        self.gemini_service = GeminiService()
        self.image_service = ImageService()
        self.storage_service = StorageService()
        self.font_manager = FontManager()
        self.prompt_validator = PromptValidator()
        self.prompt_loader = PromptLoader()

        # Stage services
        self.stage_research = StageResearchService(
            project_manager=self.project_manager,
            gemini_service=self.gemini_service,
            prompt_loader=self.prompt_loader,
        )

        self.stage_draft = StageDraftService(
            project_manager=self.project_manager,
            gemini_service=self.gemini_service,
            prompt_loader=self.prompt_loader,
        )

        self.stage_style = StageStyleService(
            project_manager=self.project_manager,
            gemini_service=self.gemini_service,
            image_service=self.image_service,
            storage_service=self.storage_service,
            prompt_loader=self.prompt_loader,
        )

        self.stage_prompts = StagePromptsService(
            project_manager=self.project_manager,
            gemini_service=self.gemini_service,
            prompt_loader=self.prompt_loader,
        )

        self.stage_images = StageImagesService(
            project_manager=self.project_manager,
            image_service=self.image_service,
            storage_service=self.storage_service,
        )

        self.rendering_service = RenderingService(
            config_manager=self.config_manager,
            font_manager=self.font_manager,
            storage_service=self.storage_service,
        )

        self.stage_typography = StageTypographyService(
            project_manager=self.project_manager,
            rendering_service=self.rendering_service,
            storage_service=self.storage_service,
        )

        self.export_service = ExportService(
            project_manager=self.project_manager,
            storage_service=self.storage_service,
        )


# Global container instance
container = ServiceContainer()


# Dependency functions for FastAPI
def get_project_manager() -> ProjectManager:
    """Provider for ProjectManager singleton."""
    return container.project_manager


def get_template_manager() -> TemplateManager:
    """Provider for TemplateManager singleton."""
    return container.template_manager


def get_gemini_service() -> GeminiService:
    """Provider for GeminiService instance."""
    return container.gemini_service


def get_image_service() -> ImageService:
    """Provider for ImageService instance."""
    return container.image_service


def get_storage_service() -> StorageService:
    """Provider for StorageService instance."""
    return container.storage_service


def get_config_manager() -> ConfigManager:
    """Provider for ConfigManager instance."""
    return container.config_manager


def get_prompt_validator() -> PromptValidator:
    """Provider for PromptValidator instance."""
    return container.prompt_validator


def get_font_manager() -> FontManager:
    """Provider for FontManager instance."""
    return container.font_manager


def get_prompt_loader() -> PromptLoader:
    """Provider for PromptLoader instance."""
    return container.prompt_loader


def get_stage_research_service() -> StageResearchService:
    """Provider for Stage Research (chat + draft extraction) service."""
    return container.stage_research


def get_stage_draft_service() -> StageDraftService:
    """Provider for Stage Draft business logic service."""
    return container.stage_draft


def get_stage_style_service() -> StageStyleService:
    """Provider for Visual Style selection service."""
    return container.stage_style


def get_stage_prompts_service() -> StagePromptsService:
    """Provider for Stage Prompts (Image Prompts) service."""
    return container.stage_prompts


def get_stage_images_service() -> StageImagesService:
    """Provider for Stage Images (Image Generation) service."""
    return container.stage_images


def get_rendering_service() -> RenderingService:
    """Provider for Typography Rendering service."""
    return container.rendering_service


def get_stage_typography_service() -> StageTypographyService:
    """Provider for Stage Typography (Design & Layout) service."""
    return container.stage_typography


def get_export_service() -> ExportService:
    """Provider for Export/ZIP service."""
    return container.export_service
