"""Stage 3 service - Image prompts to Images transformation."""

from __future__ import annotations
import asyncio
import logging
from typing import Optional, TYPE_CHECKING

from app.models.project import ProjectState

if TYPE_CHECKING:
    from app.services.project_manager import ProjectManager
    from app.services.image_service import ImageService

logger = logging.getLogger(__name__)


class Stage3Service:
    """Service for Stage 3: Image prompts to Images transformation."""

    project_manager: ProjectManager
    image_service: ImageService

    def __init__(
        self,
        project_manager: Optional[ProjectManager] = None,
        image_service: Optional[ImageService] = None,
    ):
        if not project_manager:
            raise ValueError("project_manager dependency is required")
        if not image_service:
            raise ValueError("image_service dependency is required")

        self.project_manager = project_manager
        self.image_service = image_service

    def _build_full_prompt(self, project: ProjectState, slide_index: int) -> str:
        """Combine the project's shared visual theme with slide-specific details."""
        shared_prefix = project.shared_prompt_prefix or ""
        return f"{shared_prefix} {project.slides[slide_index].image_prompt}".strip()

    async def generate_all_images(
        self,
        project_id: str,
    ) -> Optional[ProjectState]:
        """Generate images for all slides."""
        project = await self.project_manager.get_project(project_id)
        if not project or not project.slides:
            return None

        for slide in project.slides:
            if not slide.image_prompt:
                slide.image_prompt = (
                    f"Abstract professional background for slide {slide.index + 1}"
                )

        full_prompts = [
            self._build_full_prompt(project, i) for i in range(len(project.slides))
        ]
        results = await asyncio.gather(
            *(self.image_service.generate_image(prompt) for prompt in full_prompts)
        )
        for slide, image_data in zip(project.slides, results):
            slide.image_data = image_data

        await self.project_manager.update_project(project)
        return project

    async def regenerate_image(
        self,
        project_id: str,
        slide_index: int,
    ) -> Optional[ProjectState]:
        """Regenerate image for a single slide."""
        project = await self.project_manager.get_project(project_id)
        if not project or slide_index >= len(project.slides):
            return None

        slide = project.slides[slide_index]
        if not slide.image_prompt:
            slide.image_prompt = (
                f"Abstract professional background for slide {slide_index + 1}"
            )

        full_prompt = self._build_full_prompt(project, slide_index)
        slide.image_data = await self.image_service.generate_image(full_prompt)

        await self.project_manager.update_project(project)
        return project

    async def set_image_data(
        self,
        project_id: str,
        slide_index: int,
        image_data: str,
    ) -> Optional[ProjectState]:
        """Set image data directly (for uploads)."""
        project = await self.project_manager.get_project(project_id)
        if not project or slide_index >= len(project.slides):
            return None

        project.slides[slide_index].image_data = image_data
        await self.project_manager.update_project(project)
        return project
