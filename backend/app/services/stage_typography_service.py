"""Stage Typography service - Typography/layout rendering."""

from __future__ import annotations
import asyncio
import logging
from typing import Optional, Dict, Any, TYPE_CHECKING

from app.models.project import ProjectState
from app.models.style import TextStyle
from app.services.storage_service import StorageService

if TYPE_CHECKING:
    from app.services.rendering_service import RenderingService
    from app.services.project_manager import ProjectManager

logger = logging.getLogger(__name__)


class StageTypographyService:
    """Service for Stage Typography: Typography/layout rendering."""

    project_manager: ProjectManager
    rendering_service: RenderingService
    storage_service: StorageService

    def __init__(
        self,
        project_manager: Optional[ProjectManager] = None,
        rendering_service: Optional[RenderingService] = None,
        storage_service: Optional[StorageService] = None,
    ):
        if not project_manager or not rendering_service or not storage_service:
            raise ValueError("All dependencies must be provided to StageTypographyService")

        self.project_manager = project_manager
        self.rendering_service = rendering_service
        self.storage_service = storage_service

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
            if not slide.background_image_url:
                continue

            # Delete existing final_image file if it is a distinct stored file
            if slide.final_image_url and slide.final_image_url != slide.background_image_url:
                self.storage_service.delete_image(slide.final_image_url)

            if slide.text.title or slide.text.body.strip():
                # Offload CPU-bound PIL rendering to a thread so the event loop
                # is not blocked while processing each slide.
                rendered_b64 = await asyncio.to_thread(
                    self.rendering_service.render_text_on_image,
                    background_base64=slide.background_image_url,
                    style=slide.style,
                    title=slide.text.title,
                    body=slide.text.body,
                )
                slide.final_image_url = self.storage_service.save_image_to_disk(
                    rendered_b64
                )
            else:
                slide.final_image_url = slide.background_image_url

        # Update thumbnail to the first slide's final rendered image
        first_slide = project.slides[0]
        thumbnail_url = first_slide.final_image_url or first_slide.background_image_url
        if thumbnail_url:
            project.thumbnail_url = thumbnail_url

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
        if not slide.background_image_url:
            return project

        # Delete existing final_image file if it is a distinct stored file
        if slide.final_image_url and slide.final_image_url != slide.background_image_url:
            self.storage_service.delete_image(slide.final_image_url)

        if slide.text.title or slide.text.body.strip():
            rendered_b64 = await asyncio.to_thread(
                self.rendering_service.render_text_on_image,
                background_base64=slide.background_image_url,
                style=slide.style,
                title=slide.text.title,
                body=slide.text.body,
            )
            slide.final_image_url = self.storage_service.save_image_to_disk(
                rendered_b64
            )
        else:
            slide.final_image_url = slide.background_image_url

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
        if slide.background_image_url:
            suggested = await asyncio.to_thread(
                self.rendering_service.suggest_style,
                slide.background_image_url,
                slide.text.body,
            )
            slide.style = suggested
            await self.project_manager.update_project(project)

        return project
