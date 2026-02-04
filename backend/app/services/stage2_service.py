"""Stage 2 service - Slide texts to Image prompts transformation."""

import logging
from typing import Optional

from app.models.session import SessionState
from app.services.gemini_service import gemini_service
from app.services.session_manager import session_manager

logger = logging.getLogger(__name__)


IMAGE_PROMPT_GENERATION = """You are an expert visual designer creating image prompts for a social media carousel.

Given slide texts and style instructions, create image prompts that:
1. Capture the mood and emotion of each slide's message
2. Maintain visual consistency across all slides
3. Work well as backgrounds for text overlay
4. Avoid busy or cluttered compositions that would interfere with text readability
5. NEVER include text, words, or letters in the images

Style instructions: {style_instructions}

Shared visual theme: {shared_theme}

Slides to create prompts for:
{slides_text}

Create {num_prompts} image prompts, one for each slide.

Respond with a JSON object:
{{
    "shared_prefix": "A brief description of the shared visual style",
    "prompts": ["prompt for slide 1", "prompt for slide 2", ...]
}}

Each prompt should be 1-2 sentences describing the visual scene. Include:
- Main subject or scene
- Color palette or mood
- Lighting style
- Any specific visual elements

Remember: Images will have text overlaid, so backgrounds should be simple with good contrast areas.
"""


class Stage2Service:
    """Service for Stage 2: Slide texts to Image prompts transformation."""

    async def generate_all_prompts(
        self,
        session_id: str,
        image_style_instructions: Optional[str] = None,
    ) -> Optional[SessionState]:
        """Generate image prompts for all slides."""
        session = session_manager.get_session(session_id)
        if not session or not session.slides:
            return None

        # Store style instructions
        if image_style_instructions:
            session.image_style_instructions = image_style_instructions

        # Build slides text for prompt
        slides_text = "\n".join([
            f"Slide {i + 1}: {slide.text.get_full_text()}"
            for i, slide in enumerate(session.slides)
        ])

        style_instructions = session.image_style_instructions or "Modern, professional, clean aesthetic"
        shared_theme = session.shared_prompt_prefix or "Consistent visual style throughout"

        prompt = IMAGE_PROMPT_GENERATION.format(
            style_instructions=style_instructions,
            shared_theme=shared_theme,
            slides_text=slides_text,
            num_prompts=len(session.slides),
        )

        result = await gemini_service.generate_json(prompt)

        # Store shared prefix
        if result.get("shared_prefix"):
            session.shared_prompt_prefix = result["shared_prefix"]

        # Update slide prompts
        prompts = result.get("prompts", [])
        for i, slide in enumerate(session.slides):
            if i < len(prompts):
                slide.image_prompt = prompts[i]
            else:
                # Fallback prompt if not enough generated
                slide.image_prompt = f"Abstract professional background for: {slide.text.body[:50]}"

        session_manager.update_session(session)
        return session

    async def regenerate_prompt(
        self,
        session_id: str,
        slide_index: int,
    ) -> Optional[SessionState]:
        """Regenerate image prompt for a single slide."""
        session = session_manager.get_session(session_id)
        if not session or slide_index >= len(session.slides):
            return None

        slide = session.slides[slide_index]

        # Get context from surrounding slides
        context_prompts = []
        if slide_index > 0:
            context_prompts.append(f"Previous slide prompt: {session.slides[slide_index - 1].image_prompt}")
        if slide_index < len(session.slides) - 1:
            context_prompts.append(f"Next slide prompt: {session.slides[slide_index + 1].image_prompt}")

        context = "\n".join(context_prompts) if context_prompts else "This is a standalone slide."

        prompt = f"""Create a new image prompt for slide {slide_index + 1} of {len(session.slides)}.

Slide text: {slide.text.get_full_text()}

Shared visual style: {session.shared_prompt_prefix or 'Modern, professional aesthetic'}

{context}

Requirements:
- Maintain visual consistency with other slides
- Create a background suitable for text overlay
- Simple composition, no text in image
- Match the mood of the slide content

Respond with JSON:
{{"prompt": "your new image prompt here"}}
"""

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
