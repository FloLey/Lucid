"""Stage 2 service - Slide texts to Image prompts transformation."""

import asyncio
import logging
from typing import Optional

from app.models.session import SessionState
from app.services.gemini_service import gemini_service
from app.services.session_manager import session_manager
from app.services.prompt_loader import load_prompt_file

logger = logging.getLogger(__name__)


class Stage2Service:
    """Service for Stage 2: Slide texts to Image prompts transformation."""

    async def generate_all_prompts(
        self,
        session_id: str,
        image_style_instructions: Optional[str] = None,
    ) -> Optional[SessionState]:
        """Generate image prompts for all slides in parallel."""
        # Load config for defaults
        from app.services.config_manager import config_manager
        config = config_manager.get_config()

        # Fallback to config default if not provided
        if image_style_instructions is None:
            image_style_instructions = config.stage_instructions.stage2

        session = session_manager.get_session(session_id)
        if not session or not session.slides:
            return None

        # Store style instructions
        if image_style_instructions:
            session.image_style_instructions = image_style_instructions

        style_instructions = session.image_style_instructions or "Modern, professional, clean aesthetic"
        shared_theme = session.shared_prompt_prefix or "Consistent visual style throughout"

        # Get prompt template for single slide generation
        prompt_template = load_prompt_file("generate_single_image_prompt.prompt")

        # Generate prompts for each slide in parallel
        async def generate_single_prompt(slide_index: int) -> str:
            """Generate prompt for a single slide."""
            slide = session.slides[slide_index]

            # Build context with all slides
            context_parts = []
            for i, s in enumerate(session.slides):
                marker = " ← CURRENT SLIDE" if i == slide_index else ""
                context_parts.append(f"Slide {i + 1}: {s.text.get_full_text()}{marker}")

            context = "\n".join(context_parts)

            # Format style instructions
            style_instructions_text = f"Style instructions: {style_instructions}" if style_instructions else ""

            # Build prompt for this specific slide
            prompt = prompt_template.format(
                slide_text=slide.text.get_full_text(),
                shared_theme=shared_theme,
                style_instructions_text=style_instructions_text,
                context=context,
                instruction_text="",
                response_format='{"prompt": "your slide-specific image prompt here"}',
            )

            result = await gemini_service.generate_json(prompt)
            return result.get("prompt", f"Abstract professional background for: {slide.text.body[:50]}")

        # Generate all prompts in parallel
        prompts = await asyncio.gather(
            *(generate_single_prompt(i) for i in range(len(session.slides)))
        )

        # Update slide prompts
        for i, prompt in enumerate(prompts):
            session.slides[i].image_prompt = prompt

        session_manager.update_session(session)
        return session

    async def regenerate_prompt(
        self,
        session_id: str,
        slide_index: int,
        instruction: Optional[str] = None,
    ) -> Optional[SessionState]:
        """Regenerate image prompt for a single slide using the same generation logic."""
        session = session_manager.get_session(session_id)
        if not session or slide_index >= len(session.slides):
            return None

        slide = session.slides[slide_index]

        # Build context with all slides
        context_parts = []
        for i, s in enumerate(session.slides):
            marker = " ← REGENERATE THIS" if i == slide_index else ""
            context_parts.append(f"Slide {i + 1}: {s.text.get_full_text()}{marker}")

        context = "\n".join(context_parts)

        # Build instruction text
        instruction_text = f"Additional instruction for this regeneration: {instruction}" if instruction else ""

        # Reuse the same generation prompt
        style_instructions = session.image_style_instructions or "Modern, professional, clean aesthetic"
        shared_theme = session.shared_prompt_prefix or "Consistent visual style throughout"

        style_instructions_text = f"Style instructions: {style_instructions}" if style_instructions else ""

        prompt_template = load_prompt_file("generate_single_image_prompt.prompt")

        prompt = prompt_template.format(
            slide_text=slide.text.get_full_text(),
            shared_theme=shared_theme,
            style_instructions_text=style_instructions_text,
            context=context,
            instruction_text=instruction_text,
            response_format='{"prompt": "your slide-specific image prompt here"}',
        )

        result = await gemini_service.generate_json(prompt)

        if result.get("prompt"):
            slide.image_prompt = result["prompt"]
            session_manager.update_session(session)

        return session

    def update_prompt(
        self,
        session_id: str,
        slide_index: int,
        prompt: str,
    ) -> Optional[SessionState]:
        """Manually update an image prompt."""
        session = session_manager.get_session(session_id)
        if not session or slide_index >= len(session.slides):
            return None

        session.slides[slide_index].image_prompt = prompt
        session_manager.update_session(session)
        return session

    def update_style_instructions(
        self,
        session_id: str,
        style_instructions: str,
    ) -> Optional[SessionState]:
        """Update the shared style instructions."""
        session = session_manager.get_session(session_id)
        if not session:
            return None

        session.image_style_instructions = style_instructions
        session_manager.update_session(session)
        return session


# Global Stage 2 service instance
stage2_service = Stage2Service()
