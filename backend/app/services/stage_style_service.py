"""Stage Style service - Generate and select shared visual style proposals."""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from app.models.session import SessionState
from app.models.style_proposal import StyleProposal
from app.services.gemini_service import gemini_service
from app.services.image_service import image_service
from app.services.session_manager import session_manager

logger = logging.getLogger(__name__)


def _load_prompt_file(filename: str) -> str:
    """Load a prompt from the prompts directory."""
    prompt_path = Path(__file__).parent.parent.parent / "prompts" / filename
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to load prompt file {filename}: {e}")
        return ""


def _get_style_proposal_prompt() -> str:
    """Get style proposal prompt from file."""
    return _load_prompt_file("style_proposal.prompt")


class StageStyleService:
    """Service for Stage 2: Visual style proposal generation and selection."""

    async def generate_proposals(
        self,
        session_id: str,
        num_proposals: int = 3,
        additional_instructions: Optional[str] = None,
    ) -> Optional[SessionState]:
        """Generate style proposals with preview images."""
        # Load config for defaults
        from app.services.config_manager import config_manager
        config = config_manager.get_config()

        # Fallback to config default if not provided
        if additional_instructions is None:
            additional_instructions = config.stage_instructions.stage_style

        session = session_manager.get_session(session_id)
        if not session or not session.slides:
            return None

        # Build slides text summary
        slides_text = "\n".join([
            f"Slide {i + 1}: {slide.text.get_full_text()}"
            for i, slide in enumerate(session.slides)
        ])

        extra = f"Additional instructions: {additional_instructions}" if additional_instructions else ""

        # Get prompt template from config
        prompt_template = _get_style_proposal_prompt()

        response_format = '''{{
    "proposals": [
        {{
            "description": "your image generation prompt here"
        }}
    ]
}}'''

        prompt = prompt_template.format(
            num_proposals=num_proposals,
            slides_text=slides_text,
            additional_instructions=extra,
            response_format=response_format,
        )

        result = await gemini_service.generate_json(prompt)

        raw_proposals = result.get("proposals", [])

        # Generate preview images in parallel
        async def generate_preview(i: int, proposal_data: dict) -> StyleProposal:
            # Use description as the common visual style prompt
            common_flow = proposal_data.get("description", "")
            try:
                preview = await image_service.generate_image(common_flow)
            except Exception as e:
                logger.warning(f"Failed to generate preview for proposal {i}: {e}")
                preview = None

            return StyleProposal(
                index=i,
                description=common_flow,
                preview_image=preview,
            )

        proposals = await asyncio.gather(*[
            generate_preview(i, p) for i, p in enumerate(raw_proposals)
        ])

        session.style_proposals = list(proposals)
        session.selected_style_proposal_index = None
        session_manager.update_session(session)
        return session

    def select_proposal(
        self,
        session_id: str,
        proposal_index: int,
    ) -> Optional[SessionState]:
        """Select a style proposal and set shared_prompt_prefix."""
        session = session_manager.get_session(session_id)
        if not session:
            return None

        if proposal_index < 0 or proposal_index >= len(session.style_proposals):
            return None

        proposal = session.style_proposals[proposal_index]
        session.shared_prompt_prefix = proposal.description
        session.selected_style_proposal_index = proposal_index
        session_manager.update_session(session)
        return session


# Global instance
stage_style_service = StageStyleService()
