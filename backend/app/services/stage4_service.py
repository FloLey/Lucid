"""Stage 4 service - Typography/layout rendering."""

from __future__ import annotations
import logging
from typing import Optional, Dict, Any, TYPE_CHECKING

from app.models.project import ProjectState
from app.models.style import TextStyle

if TYPE_CHECKING:
    from app.services.rendering_service import RenderingService
    from app.services.project_manager import ProjectManager

logger = logging.getLogger(__name__)


class Stage4Service:
    """Service for Stage 4: Typography/layout rendering."""

    project_manager: ProjectManager
    rendering_service: RenderingService

    def __init__(
        self,
        project_manager: Optional[ProjectManager] = None,
        rendering_service: Optional[RenderingService] = None,
    ):
        if not project_manager or not rendering_service:
            raise ValueError("All dependencies must be provided to Stage4Service")

        self.project_manager = project_manager
        self.rendering_service = rendering_service

    async def apply_text_to_all_images(
        self,
        project_id: str,
        use_ai_suggestions: bool = True,
    ) -> Optional[ProjectState]:
        """Apply text styling to all slide images."""
        project = await self.project_manager.get_project(project_id)
        if not project or not project.slides:
            return None

        for slide in project.slides:
            if not slide.image_data:
                continue

            if slide.text.title or slide.text.body.strip():
                slide.final_image = self.rendering_service.render_text_on_image(
                    background_base64=slide.image_data,
                    style=slide.style,
                    title=slide.text.title,
                    body=slide.text.body,
                )
            else:
                slide.final_image = slide.image_data

        await self.project_manager.update_project(project)
        return project

    async def apply_text_to_image(
        self,
        project_id: str,
        slide_index: int,
    ) -> Optional[ProjectState]:
        """Apply text styling to a single slide image."""
        project = await self.project_manager.get_project(project_id)
        if not project or slide_index >= len(project.slides):
            return None

        slide = project.slides[slide_index]
        if not slide.image_data:
            return project

        if slide.text.title or slide.text.body.strip():
            slide.final_image = self.rendering_service.render_text_on_image(
                background_base64=slide.image_data,
                style=slide.style,
                title=slide.text.title,
                body=slide.text.body,
            )
        else:
            slide.final_image = slide.image_data

        await self.project_manager.update_project(project)
        return project

    def _deep_merge_style(self, style: TextStyle, updates: Dict[str, Any]) -> TextStyle:
        """Merge partial updates into a TextStyle, handling nested sub-models."""
        current = style.model_dump()
        for key, value in updates.items():
            if (
                key in current
                and isinstance(current[key], dict)
                and isinstance(value, dict)
            ):
                current[key] = {**current[key], **value}
            else:
                current[key] = value
        return TextStyle(**current)

    async def update_style(
        self,
        project_id: str,
        slide_index: int,
        style_updates: Dict[str, Any],
    ) -> Optional[ProjectState]:
        """Update style properties for a slide."""
        project = await self.project_manager.get_project(project_id)
        if not project or slide_index >= len(project.slides):
            return None

        slide = project.slides[slide_index]
        slide.style = self._deep_merge_style(slide.style, style_updates)

        await self.project_manager.update_project(project)
        return project

    async def apply_style_to_all(
        self,
        project_id: str,
        style_updates: Dict[str, Any],
    ) -> Optional[ProjectState]:
        """Apply style updates to all slides."""
        project = await self.project_manager.get_project(project_id)
        if not project or not project.slides:
            return None

        for slide in project.slides:
            slide.style = self._deep_merge_style(slide.style, style_updates)

        await self.project_manager.update_project(project)
        return project

    async def suggest_style(
        self,
        project_id: str,
        slide_index: int,
    ) -> Optional[ProjectState]:
        """Use image analysis to suggest optimal style for a slide."""
        project = await self.project_manager.get_project(project_id)
        if not project or slide_index >= len(project.slides):
            return None

        slide = project.slides[slide_index]
        if slide.image_data:
            suggested = self.rendering_service.suggest_style(
                slide.image_data, slide.text.body
            )
            slide.style = suggested
            await self.project_manager.update_project(project)

        return project
