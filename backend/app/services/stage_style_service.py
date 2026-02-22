"""Stage Style service - Generate and select shared visual style proposals."""

from __future__ import annotations
import logging
from typing import Optional, TYPE_CHECKING

from app.models.project import ProjectState
from app.models.style_proposal import StyleProposal
from app.services.async_utils import bounded_gather
from app.services.base_stage_service import BaseStageService
from app.services.prompt_loader import PromptLoader
from app.services.storage_service import StorageService
from app.services.llm_logger import set_project_context

if TYPE_CHECKING:
    from app.services.project_manager import ProjectManager
    from app.services.gemini_service import GeminiService
    from app.services.image_service import ImageService

logger = logging.getLogger(__name__)


class StageStyleService(BaseStageService):
    """Service for Stage Style: Visual style proposal generation and selection."""

    project_manager: ProjectManager
    gemini_service: GeminiService
    image_service: ImageService
    storage_service: StorageService

    def __init__(
        self,
        project_manager: Optional[ProjectManager] = None,
        gemini_service: Optional[GeminiService] = None,
        image_service: Optional[ImageService] = None,
        storage_service: Optional[StorageService] = None,
        prompt_loader: Optional[PromptLoader] = None,
    ):
        self.project_manager = self._require(project_manager, "project_manager")
        self.gemini_service = self._require(gemini_service, "gemini_service")
        self.image_service = self._require(image_service, "image_service")
        self.storage_service = self._require(storage_service, "storage_service")
        self.prompt_loader = prompt_loader or PromptLoader()

    async def generate_proposals(
        self,
        project_id: str,
        num_proposals: int = 3,
        additional_instructions: Optional[str] = None,
        concurrency_limit: int = 5,
    ) -> Optional[ProjectState]:
        """Generate style proposals with preview images."""
        set_project_context(project_id)
        project = await self.project_manager.get_project(project_id)
        if not project or not project.slides:
            return None

        slides_text = "\n".join(
            [
                f"Slide {i + 1}: {slide.text.get_full_text()}"
                for i, slide in enumerate(project.slides)
            ]
        )

        extra = (
            f"Additional instructions: {additional_instructions}"
            if additional_instructions
            else ""
        )

        prompt_template = self.prompt_loader.resolve_prompt(project, "style_proposal")

        response_format = (
            """{{\n    "proposals": [\n        {{\n"""
            """            "description": "your image generation prompt here"\n"""
            """        }}\n    ]\n}}"""
        )

        prompt = prompt_template.format(
            num_proposals=num_proposals,
            slides_text=slides_text,
            additional_instructions=extra,
            response_format=response_format,
        )

        result = await self.gemini_service.generate_json(
            prompt, caller="stage_style_service.generate_proposals"
        )

        raw_proposals = result.get("proposals", [])

        async def generate_preview(i: int, proposal_data: dict) -> StyleProposal:
            common_flow = proposal_data.get("description", "")
            preview_path: Optional[str] = None
            try:
                b64 = await self.image_service.generate_image(common_flow)
                preview_path = self.storage_service.save_image_to_disk(b64)
            except Exception as e:
                logger.warning(f"Failed to generate preview for proposal {i}: {e}")

            return StyleProposal(
                index=i,
                description=common_flow,
                preview_image=preview_path,
            )

        proposals = await bounded_gather(
            [generate_preview(i, p) for i, p in enumerate(raw_proposals)],
            concurrency_limit,
        )

        old_proposals = project.style_proposals
        project.style_proposals = list(proposals)
        # Delete old proposal preview images from disk after replacing them
        for old in old_proposals:
            self.storage_service.delete_image(old.preview_image)
        project.selected_style_proposal_index = None
        # Use the first proposal's preview as the initial thumbnail
        if proposals and proposals[0].preview_image:
            project.thumbnail_url = proposals[0].preview_image
        await self.project_manager.update_project(project)
        return project

    async def select_proposal(
        self,
        project_id: str,
        proposal_index: int,
    ) -> Optional[ProjectState]:
        """Select a style proposal and set shared_prompt_prefix."""
        project = await self.project_manager.get_project(project_id)
        if not project:
            return None

        if proposal_index < 0 or proposal_index >= len(project.style_proposals):
            return None

        proposal = project.style_proposals[proposal_index]
        project.shared_prompt_prefix = proposal.description
        project.selected_style_proposal_index = proposal_index
        # Update thumbnail to reflect the chosen style
        if proposal.preview_image:
            project.thumbnail_url = proposal.preview_image
        await self.project_manager.update_project(project)
        return project
