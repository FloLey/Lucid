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
from app.services.stage1_service import Stage1Service
from app.services.stage_style_service import StageStyleService
from app.services.stage2_service import Stage2Service
from app.services.stage3_service import Stage3Service
from app.services.stage4_service import Stage4Service
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
        self.font_manager = FontManager()
        self.prompt_validator = PromptValidator()
        self.prompt_loader = PromptLoader()

        # Stage services
        self.stage1 = Stage1Service(
            project_manager=self.project_manager,
            gemini_service=self.gemini_service,
        )

        self.stage_style = StageStyleService(
            project_manager=self.project_manager,
            gemini_service=self.gemini_service,
            image_service=self.image_service,
        )

        self.stage2 = Stage2Service(
            project_manager=self.project_manager,
            gemini_service=self.gemini_service,
        )

        self.stage3 = Stage3Service(
            project_manager=self.project_manager,
            image_service=self.image_service,
        )

        self.rendering_service = RenderingService(
            config_manager=self.config_manager,
            font_manager=self.font_manager,
            image_service=self.image_service,
        )

        self.stage4 = Stage4Service(
            project_manager=self.project_manager,
            rendering_service=self.rendering_service,
        )

        self.export_service = ExportService(
            project_manager=self.project_manager,
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


def get_stage1_service() -> Stage1Service:
    """Provider for Stage 1 business logic service."""
    return container.stage1


def get_stage_style_service() -> StageStyleService:
    """Provider for Visual Style selection service."""
    return container.stage_style


def get_stage2_service() -> Stage2Service:
    """Provider for Stage 2 (Image Prompts) service."""
    return container.stage2


def get_stage3_service() -> Stage3Service:
    """Provider for Stage 3 (Image Generation) service."""
    return container.stage3


def get_rendering_service() -> RenderingService:
    """Provider for Typography Rendering service."""
    return container.rendering_service


def get_stage4_service() -> Stage4Service:
    """Provider for Stage 4 (Design & Layout) service."""
    return container.stage4


def get_export_service() -> ExportService:
    """Provider for Export/ZIP service."""
    return container.export_service
