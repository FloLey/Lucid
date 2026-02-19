"""Stage 1 service - Draft to Slide texts transformation."""

from __future__ import annotations
import logging
from typing import Optional, TYPE_CHECKING

from app.models.slide import Slide, SlideText
from app.models.session import SessionState
from app.services.prompt_loader import load_prompt_file

if TYPE_CHECKING:
    from app.services.session_manager import SessionManager
    from app.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)


class Stage1Service:
    """Service for Stage 1: Draft to Slide texts transformation."""

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

    @staticmethod
    def _build_title_instruction(include_titles: bool) -> str:
        """Generate instructions for the LLM regarding slide titles."""
        if include_titles:
            return "Each slide MUST have both a title and body."
        return "Each slide should only have body text (no titles)."

    @staticmethod
    def _build_slide_format(include_titles: bool) -> str:
        """Describe the expected JSON fields per slide."""
        if include_titles:
            return '"title" (string) and "body" (string)'
        return '"body" (string) only'

    @staticmethod
    def _build_response_format(include_titles: bool) -> str:
        """Provide a JSON schema example for the LLM response."""
        if include_titles:
            return '{"slides": [{"title": "Hook", "body": "Grab attention here"}, ...]}'
        return '{"slides": [{"body": "First slide content"}, ...]}'

    async def generate_slide_texts(
        self,
        session_id: str,
        draft_text: str,
        num_slides: Optional[int] = None,
        include_titles: bool = True,
        additional_instructions: Optional[str] = None,
        language: str = "English",
    ) -> Optional[SessionState]:
        """Generate slide texts from a draft.

        All config defaults should be resolved by the caller (route handler).
        """
        session = await self.session_manager.get_session(session_id)
        if not session:
            session = await self.session_manager.create_session(session_id)

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

        title_instruction = self._build_title_instruction(include_titles)
        slide_format = self._build_slide_format(include_titles)
        response_format = self._build_response_format(include_titles)

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
        result = await self.gemini_service.generate_json(
            prompt, caller="stage1_service.generate_slide_texts"
        )

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

        await self.session_manager.update_session(session)
        return session

    async def regenerate_all_slide_texts(
        self,
        session_id: str,
    ) -> Optional[SessionState]:
        """Regenerate all slide texts using stored inputs."""
        session = await self.session_manager.get_session(session_id)
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
        session = await self.session_manager.get_session(session_id)
        if not session or slide_index >= len(session.slides):
            return None

        instruction_text = (
            f"\nSpecific instruction: {instruction}" if instruction else ""
        )

        language_instruction = f"Write ALL slide content in {session.language}."

        title_instruction = (
            "Include both title and body."
            if session.include_titles
            else "Only provide body text."
        )
        response_format = '{"title": "...", "body": "..."}'

        # Build all-slides context with current slide marked
        all_slides_parts = []
        for i, s in enumerate(session.slides):
            marker = " ← CURRENT SLIDE" if i == slide_index else ""
            all_slides_parts.append(f"Slide {i + 1}: {s.text.get_full_text()}{marker}")
        all_slides_context = "\n".join(all_slides_parts)

        prompt_template = load_prompt_file("regenerate_single_slide.prompt")

        prompt = prompt_template.format(
            draft_text=session.draft_text,
            language_instruction=language_instruction,
            all_slides_context=all_slides_context,
            current_text=session.slides[slide_index].text.get_full_text(),
            instruction_text=instruction_text,
            title_instruction=title_instruction,
            response_format=response_format,
        )

        result = await self.gemini_service.generate_json(
            prompt, caller="stage1_service.regenerate_slide_text"
        )

        if result:
            session.slides[slide_index].text = SlideText(
                title=result.get("title") if session.include_titles else None,
                body=result.get("body", session.slides[slide_index].text.body),
            )
            await self.session_manager.update_session(session)

        return session

    async def update_slide_text(
        self,
        session_id: str,
        slide_index: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
    ) -> Optional[SessionState]:
        """Manually update a slide's text."""
        session = await self.session_manager.get_session(session_id)
        if not session or slide_index >= len(session.slides):
            return None

        slide = session.slides[slide_index]
        if title is not None:
            slide.text.title = title
        if body is not None:
            slide.text.body = body

        await self.session_manager.update_session(session)
        return session
