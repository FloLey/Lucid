"""Stage 1 service - Draft to Slide texts transformation."""

import logging
from typing import List, Optional

from app.models.slide import Slide, SlideText
from app.models.session import SessionState
from app.services.gemini_service import gemini_service
from app.services.session_manager import session_manager
from app.services.prompt_loader import load_prompt_file

logger = logging.getLogger(__name__)


class Stage1Service:
    """Service for Stage 1: Draft to Slide texts transformation."""

    async def generate_slide_texts(
        self,
        session_id: str,
        draft_text: str,
        num_slides: Optional[int] = None,
        include_titles: Optional[bool] = None,
        additional_instructions: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Optional[SessionState]:
        """Generate slide texts from a draft."""
        # Load config for defaults
        from app.services.config_manager import config_manager
        config = config_manager.get_config()

        # Fallback chain: explicit param -> config default -> built-in default
        if num_slides is None:
            num_slides = config.global_defaults.num_slides  # Can also be None!
        if language is None:
            language = config.global_defaults.language
        if include_titles is None:
            include_titles = config.global_defaults.include_titles
        if additional_instructions is None:
            additional_instructions = config.stage_instructions.stage1

        session = session_manager.get_session(session_id)
        if not session:
            session = session_manager.create_session(session_id)

        # Store inputs
        session.draft_text = draft_text
        session.num_slides = num_slides
        session.include_titles = include_titles
        session.additional_instructions = additional_instructions
        session.language = language

        # Build prompt with dynamic num_slides instruction
        if num_slides is not None:
            num_slides_instruction = f"Generate exactly {num_slides} slides."
        else:
            num_slides_instruction = "Choose the optimal number of slides based on the content (maximum 10 slides)."

        language_instruction = f"Write ALL slide content in {language}."

        title_instruction = (
            "Each slide MUST have both a title and body."
            if include_titles
            else "Each slide should only have body text (no titles)."
        )

        slide_format = (
            '"title" (string) and "body" (string)'
            if include_titles
            else '"body" (string) only'
        )

        response_format = (
            '{"slides": [{"title": "Hook", "body": "Grab attention here"}, ...]}'
            if include_titles
            else '{"slides": [{"body": "First slide content"}, ...]}'
        )

        additional = (
            f"Additional instructions: {additional_instructions}"
            if additional_instructions
            else ""
        )

        prompt_template = load_prompt_file("slide_generation.prompt")

        prompt = prompt_template.format(
            num_slides_instruction=num_slides_instruction,
            language_instruction=language_instruction,
            title_instruction=title_instruction,
            additional_instructions=additional,
            draft=draft_text,
            slide_format=slide_format,
            response_format=response_format,
        )

        # Generate with Gemini
        result = await gemini_service.generate_json(prompt)

        # Parse and store slides
        slides_data = result.get("slides", [])
        session.slides = []

        # If num_slides was specified, use it as a limit/target
        # If None, AI decided the count (but cap at 10 for safety)
        max_slides = num_slides if num_slides is not None else 10

        for i, slide_data in enumerate(slides_data[:max_slides]):
            slide = Slide(
                index=i,
                text=SlideText(
                    title=slide_data.get("title") if include_titles else None,
                    body=slide_data.get("body", ""),
                ),
            )
            session.slides.append(slide)

        # Only pad if num_slides was explicitly specified
        if num_slides is not None:
            while len(session.slides) < num_slides:
                session.slides.append(
                    Slide(
                        index=len(session.slides),
                        text=SlideText(body=f"Slide {len(session.slides) + 1} content"),
                    )
                )

        # Update session.num_slides to reflect actual count
        session.num_slides = len(session.slides)

        session_manager.update_session(session)
        return session

    async def regenerate_all_slide_texts(
        self,
        session_id: str,
    ) -> Optional[SessionState]:
        """Regenerate all slide texts using stored inputs."""
        session = session_manager.get_session(session_id)
        if not session or not session.draft_text:
            return None

        return await self.generate_slide_texts(
            session_id=session_id,
            draft_text=session.draft_text,
            num_slides=session.num_slides,
            include_titles=session.include_titles,
            additional_instructions=session.additional_instructions,
            language=session.language,
        )

    async def regenerate_slide_text(
        self,
        session_id: str,
        slide_index: int,
        instruction: Optional[str] = None,
    ) -> Optional[SessionState]:
        """Regenerate a single slide text."""
        session = session_manager.get_session(session_id)
        if not session or slide_index >= len(session.slides):
            return None

        # Get context from surrounding slides
        prev_context = ""
        next_context = ""

        if slide_index > 0:
            prev_slide = session.slides[slide_index - 1]
            prev_context = f"Previous slide: {prev_slide.text.get_full_text()}"

        if slide_index < len(session.slides) - 1:
            next_slide = session.slides[slide_index + 1]
            next_context = f"Next slide: {next_slide.text.get_full_text()}"

        instruction_text = f"\nSpecific instruction: {instruction}" if instruction else ""

        title_instruction = (
            "Include both title and body."
            if session.include_titles
            else "Only provide body text."
        )

        response_format = '{"title": "...", "body": "..."}'

        prompt_template = load_prompt_file("regenerate_single_slide.prompt")

        prompt = prompt_template.format(
            slide_num=slide_index + 1,
            total_slides=len(session.slides),
            language=session.language,
            draft_text=session.draft_text,
            prev_context=prev_context,
            next_context=next_context,
            current_text=session.slides[slide_index].text.get_full_text(),
            instruction_text=instruction_text,
            title_instruction=title_instruction,
            response_format=response_format,
        )

        result = await gemini_service.generate_json(prompt)

        if result:
            session.slides[slide_index].text = SlideText(
                title=result.get("title") if session.include_titles else None,
                body=result.get("body", session.slides[slide_index].text.body),
            )
            session_manager.update_session(session)

        return session

    def update_slide_text(
        self,
        session_id: str,
        slide_index: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
    ) -> Optional[SessionState]:
        """Manually update a slide's text."""
        session = session_manager.get_session(session_id)
        if not session or slide_index >= len(session.slides):
            return None

        slide = session.slides[slide_index]
        if title is not None:
            slide.text.title = title
        if body is not None:
            slide.text.body = body

        session_manager.update_session(session)
        return session


# Global Stage 1 service instance
stage1_service = Stage1Service()
