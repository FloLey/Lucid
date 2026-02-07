"""Stage Style service - Generate and select shared visual style proposals."""

import asyncio
import logging
from typing import Optional

from app.models.session import SessionState
from app.models.style_proposal import StyleProposal
from app.services.gemini_service import gemini_service
from app.services.image_service import image_service
from app.services.session_manager import session_manager

logger = logging.getLogger(__name__)


STYLE_PROPOSAL_PROMPT = """You are an expert visual designer creating shared visual style proposals for a social media carousel.

Given the slide texts below, propose {num_proposals} distinct visual styles that would work well as consistent background themes across all slides.

Slides:
{slides_text}

{additional_instructions}

For each proposal, provide:
1. A "description": A shared image prompt prefix that will be prepended to every per-slide image prompt. Write it as a direct image generation directive — NOT a human-readable description. It should specify the visual style, color palette, lighting, texture, and mood in prompt form.
   GOOD example: "Soft watercolor washes in muted earth tones, warm diffused lighting, textured paper background, gentle organic shapes"
   BAD example: "This style evokes a warm, natural feeling with earthy watercolor tones"
2. An "image_prompt": A complete standalone image generation prompt for a preview image that applies this style.

Respond with a JSON object:
{{
    "proposals": [
        {{
            "description": "shared prompt prefix here",
            "image_prompt": "complete image prompt for preview"
        }}
    ]
}}

Each style should be meaningfully different from the others. Styles should:
- Work well as backgrounds for text overlay (not too busy)
- Maintain visual consistency suitable for a carousel
- Have clear, distinct color palettes and moods
- NEVER include text, words, or letters in images
"""


class StageStyleService:
    """Service for Stage 2: Visual style proposal generation and selection."""

    async def generate_proposals(
        self,
        session_id: str,
        num_proposals: int = 3,
        additional_instructions: Optional[str] = None,
    ) -> Optional[SessionState]:
        """Generate style proposals with preview images."""
        session = session_manager.get_session(session_id)
        if not session or not session.slides:
            return None

        # Build slides text summary
        slides_text = "\n".join([
            f"Slide {i + 1}: {slide.text.get_full_text()}"
            for i, slide in enumerate(session.slides)
        ])

        extra = f"Additional instructions: {additional_instructions}" if additional_instructions else ""

        prompt = STYLE_PROPOSAL_PROMPT.format(
            num_proposals=num_proposals,
            slides_text=slides_text,
            additional_instructions=extra,
        )

        result = await gemini_service.generate_json(prompt)

        raw_proposals = result.get("proposals", [])

        # Generate preview images in parallel
        async def generate_preview(i: int, proposal_data: dict) -> StyleProposal:
            image_prompt = proposal_data.get("image_prompt", proposal_data.get("description", ""))
            try:
                preview = await image_service.generate_image(image_prompt)
            except Exception as e:
                logger.warning(f"Failed to generate preview for proposal {i}: {e}")
                preview = None

            return StyleProposal(
                index=i,
                description=proposal_data.get("description", ""),
                image_prompt=image_prompt,
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
