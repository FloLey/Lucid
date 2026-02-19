"""Stage Style service - Generate and select shared visual style proposals."""

from __future__ import annotations
import asyncio
import logging
from typing import Optional, TYPE_CHECKING

from app.models.session import SessionState
from app.models.style_proposal import StyleProposal
from app.services.prompt_loader import load_prompt_file

if TYPE_CHECKING:
    from app.services.session_manager import SessionManager
    from app.services.gemini_service import GeminiService
    from app.services.image_service import ImageService

logger = logging.getLogger(__name__)


class StageStyleService:
    """Service for Stage 2: Visual style proposal generation and selection."""

    session_manager: SessionManager
    gemini_service: GeminiService
    image_service: ImageService

    def __init__(
        self,
        session_manager: Optional[SessionManager] = None,
        gemini_service: Optional[GeminiService] = None,
        image_service: Optional[ImageService] = None,
    ):
        # Validate dependencies before assignment
        if not session_manager:
            raise ValueError("session_manager dependency is required")
        if not gemini_service:
            raise ValueError("gemini_service dependency is required")
        if not image_service:
            raise ValueError("image_service dependency is required")

        self.session_manager = session_manager
        self.gemini_service = gemini_service
        self.image_service = image_service

    async def generate_proposals(
        self,
        session_id: str,
        num_proposals: int = 3,
        additional_instructions: Optional[str] = None,
    ) -> Optional[SessionState]:
        """Generate style proposals with preview images.

        additional_instructions should be resolved by the caller (route handler).
        """
        session = await self.session_manager.get_session(session_id)
        if not session or not session.slides:
            return None

        # Build slides text summary
        slides_text = "\n".join(
            [
                f"Slide {i + 1}: {slide.text.get_full_text()}"
                for i, slide in enumerate(session.slides)
            ]
        )

        extra = (
            f"Additional instructions: {additional_instructions}"
            if additional_instructions
            else ""
        )

        # Get prompt template from config
        prompt_template = load_prompt_file("style_proposal.prompt")

        response_format = """{{\n    "proposals": [\n        {{\n            "description": "your image generation prompt here"\n        }}\n    ]\n}}"""

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

        # Generate preview images in parallel
        async def generate_preview(i: int, proposal_data: dict) -> StyleProposal:
            # Use description as the common visual style prompt
            common_flow = proposal_data.get("description", "")
            try:
                preview = await self.image_service.generate_image(common_flow)
            except Exception as e:
                logger.warning(f"Failed to generate preview for proposal {i}: {e}")
                preview = None

            return StyleProposal(
                index=i,
                description=common_flow,
                preview_image=preview,
            )

        proposals = await asyncio.gather(
            *[generate_preview(i, p) for i, p in enumerate(raw_proposals)]
        )

        session.style_proposals = list(proposals)
        session.selected_style_proposal_index = None
        await self.session_manager.update_session(session)
        return session

    async def select_proposal(
        self,
        session_id: str,
        proposal_index: int,
    ) -> Optional[SessionState]:
        """Select a style proposal and set shared_prompt_prefix."""
        session = await self.session_manager.get_session(session_id)
        if not session:
            return None

        if proposal_index < 0 or proposal_index >= len(session.style_proposals):
            return None

        proposal = session.style_proposals[proposal_index]
        session.shared_prompt_prefix = proposal.description
        session.selected_style_proposal_index = proposal_index
        await self.session_manager.update_session(session)
        return session
