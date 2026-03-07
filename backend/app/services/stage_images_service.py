"""Stage Images service - Image prompts to Images transformation."""

from __future__ import annotations
import logging
from typing import Optional, TYPE_CHECKING

from app.models.project import ProjectState
from app.services.base_stage_service import BaseStageService
from app.services.storage_service import StorageService

if TYPE_CHECKING:
    from app.services.project_manager import ProjectManager
    from app.services.image_service import ImageService

logger = logging.getLogger(__name__)

_DEFAULT_IMAGE_PROMPT = "Abstract professional background for slide {n}"


class StageImagesService(BaseStageService):
    """Service for Stage Images: Image prompts to Images transformation."""

    project_manager: ProjectManager
    image_service: ImageService
    storage_service: StorageService

    def __init__(
        self,
        project_manager: Optional[ProjectManager] = None,
        image_service: Optional[ImageService] = None,
        storage_service: Optional[StorageService] = None,
    ):
        self.project_manager = self._require(project_manager, "project_manager")
        self.image_service = self._require(image_service, "image_service")
        self.storage_service = self._require(storage_service, "storage_service")

    def _build_full_prompt(self, project: ProjectState, slide_index: int) -> str:
        """Combine the project's shared visual theme with slide-specific details."""
        shared_prefix = project.shared_prompt_prefix or ""
        return f"{shared_prefix} {project.slides[slide_index].image_prompt}".strip()

    async def generate_all_images(
        self,
        project_id: str,
        concurrency_limit: int = 10,
    ) -> Optional[ProjectState]:
        """Generate images for all slides."""
        project = await self.project_manager.get_project(project_id)
        if not project or not project.slides:
            return None

        for slide in project.slides:
            if not slide.image_prompt:
                slide.image_prompt = _DEFAULT_IMAGE_PROMPT.format(n=slide.index + 1)

        full_prompts = [
            self._build_full_prompt(project, i) for i in range(len(project.slides))
        ]

        # Delete existing background images before overwriting
        for slide in project.slides:
            await self.storage_service.delete_image(slide.background_image_url)

        results = await self._batch(
            [self.image_service.generate_image(p) for p in full_prompts],
            limit=concurrency_limit,
            return_exceptions=True,
        )
        for slide, result in zip(project.slides, results):
            if isinstance(result, BaseException):
                logger.warning(
                    "Image generation failed for slide %d: %s",
                    slide.index,
                    result,
                )
                # Preserve existing image on failure rather than losing it
                continue
            slide.background_image_url = await self.storage_service.save_image_to_disk(result)

        # Update thumbnail to the first slide's background image
        if project.slides and project.slides[0].background_image_url:
            project.thumbnail_url = project.slides[0].background_image_url

        await self.project_manager.update_project(project)
        return project

    async def regenerate_image(
        self,
        project_id: str,
        slide_index: int,
    ) -> Optional[ProjectState]:
        """Regenerate image for a single slide."""
        async with self._project_ctx(project_id) as project:
            if not self._valid_slide(project, slide_index):
                return None

            slide = project.slides[slide_index]
            if not slide.image_prompt:
                slide.image_prompt = _DEFAULT_IMAGE_PROMPT.format(n=slide_index + 1)

            full_prompt = self._build_full_prompt(project, slide_index)
            # Delete existing background image before overwriting
            await self.storage_service.delete_image(slide.background_image_url)
            b64 = await self.image_service.generate_image(full_prompt)
            slide.background_image_url = await self.storage_service.save_image_to_disk(b64)

            # Keep the project thumbnail in sync: if this slide was the thumbnail source,
            # update it so the project list doesn't show a broken image.
            if slide_index == 0:
                project.thumbnail_url = slide.background_image_url

        return project

    async def set_image_data(
        self,
        project_id: str,
        slide_index: int,
        image_data: str,
    ) -> Optional[ProjectState]:
        """Set image data directly (for uploads)."""
        async with self._project_ctx(project_id) as project:
            if not self._valid_slide(project, slide_index):
                return None

            project.slides[slide_index].background_image_url = image_data

        return project
