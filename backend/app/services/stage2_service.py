"""Stage 2 service - Slide texts to Image prompts transformation."""

from __future__ import annotations
import asyncio
import logging
from typing import Optional, TYPE_CHECKING

from app.models.session import SessionState
from app.services.prompt_loader import load_prompt_file

if TYPE_CHECKING:
    from app.services.session_manager import SessionManager
    from app.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)


class Stage2Service:
    """Service for Stage 2: Slide texts to Image prompts transformation."""

    session_manager: SessionManager
    gemini_service: GeminiService

    def __init__(
        self,
        session_manager: Optional[SessionManager] = None,
        gemini_service: Optional[GeminiService] = None,
    ):
        # Validate dependencies before assignment
        if not session_manager:
            raise ValueError("session_manager dependency is required")
        if not gemini_service:
            raise ValueError("gemini_service dependency is required")

        self.session_manager = session_manager
        self.gemini_service = gemini_service

    def _build_slide_prompt(
        self,
        session: SessionState,
        slide_index: int,
        instruction: Optional[str] = None,
    ) -> str:
        """
        Build the LLM prompt for generating a visual concepts description.

        Args:
            session: The current session state.
            slide_index: The target slide.
            instruction: Optional user-provided refinement instruction.
        """
        style_instructions = (
            session.image_style_instructions or "Modern, professional, clean aesthetic"
        )
        shared_theme = (
            session.shared_prompt_prefix or "Consistent visual style throughout"
        )

        # Build context with all slides
        context_parts = []
        for i, s in enumerate(session.slides):
            marker = " ← CURRENT SLIDE" if i == slide_index else ""
            context_parts.append(f"Slide {i + 1}: {s.text.get_full_text()}{marker}")
        context = "\n".join(context_parts)

        style_instructions_text = (
            f"Style instructions: {style_instructions}" if style_instructions else ""
        )
        instruction_text = (
            f"Additional instruction for this regeneration: {instruction}"
            if instruction
            else ""
        )

        prompt_template = load_prompt_file("generate_single_image_prompt.prompt")
        return prompt_template.format(
            slide_text=session.slides[slide_index].text.get_full_text(),
            shared_theme=shared_theme,
            style_instructions_text=style_instructions_text,
            context=context,
            instruction_text=instruction_text,
            response_format='{"prompt": "your slide-specific image prompt here"}',
        )

    async def generate_all_prompts(
        self,
        session_id: str,
        image_style_instructions: Optional[str] = None,
    ) -> Optional[SessionState]:
        """Generate image prompts for all slides in parallel.

        image_style_instructions should be resolved by the caller (route handler).
        """
        session = await self.session_manager.get_session(session_id)
        if not session or not session.slides:
            return None

        # Store style instructions
        if image_style_instructions:
            session.image_style_instructions = image_style_instructions

        # Generate prompts for each slide in parallel
        async def generate_single_prompt(slide_index: int) -> str:
            """Generate prompt for a single slide."""
            prompt = self._build_slide_prompt(session, slide_index)
            result = await self.gemini_service.generate_json(
                prompt, caller="stage2_service.generate_single_prompt"
            )
            return result.get(
                "prompt",
                f"Abstract professional background for: {session.slides[slide_index].text.body[:50]}",
            )

        # Generate all prompts in parallel
        prompts = await asyncio.gather(
            *(generate_single_prompt(i) for i in range(len(session.slides)))
        )

        # Update slide prompts
        for i, prompt in enumerate(prompts):
            session.slides[i].image_prompt = prompt

        await self.session_manager.update_session(session)
        return session

    async def regenerate_prompt(
        self,
        session_id: str,
        slide_index: int,
        instruction: Optional[str] = None,
    ) -> Optional[SessionState]:
        """Regenerate image prompt for a single slide using the same generation logic."""
        session = await self.session_manager.get_session(session_id)
        if not session or slide_index >= len(session.slides):
            return None

        prompt = self._build_slide_prompt(session, slide_index, instruction=instruction)
        result = await self.gemini_service.generate_json(
            prompt, caller="stage2_service.regenerate_prompt"
        )

        if result.get("prompt"):
            session.slides[slide_index].image_prompt = result["prompt"]
            await self.session_manager.update_session(session)

        return session

    async def update_prompt(
        self,
        session_id: str,
        slide_index: int,
        prompt: str,
    ) -> Optional[SessionState]:
        """Manually update an image prompt."""
        session = await self.session_manager.get_session(session_id)
        if not session or slide_index >= len(session.slides):
            return None

        session.slides[slide_index].image_prompt = prompt
        await self.session_manager.update_session(session)
        return session

    async def update_style_instructions(
        self,
        session_id: str,
        style_instructions: str,
    ) -> Optional[SessionState]:
        """Update the shared style instructions."""
        session = await self.session_manager.get_session(session_id)
        if not session:
            return None

        session.image_style_instructions = style_instructions
        await self.session_manager.update_session(session)
        return session
