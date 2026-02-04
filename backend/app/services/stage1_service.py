"""Stage 1 service - Draft to Slide texts transformation."""

import logging
from typing import List, Optional

from app.models.slide import Slide, SlideText
from app.models.session import SessionState
from app.services.gemini_service import gemini_service
from app.services.session_manager import session_manager

logger = logging.getLogger(__name__)


SLIDE_GENERATION_PROMPT = """You are an expert content strategist helping create carousel slides for social media.

Given a draft text, create {num_slides} slide texts that:
1. Transform the rough draft into clear, engaging messages
2. Each slide should have a single focused message
3. Use conversational, engaging language
4. Maintain logical flow between slides
5. First slide should hook the reader
6. Last slide should have a clear call-to-action

{title_instruction}

{additional_instructions}

Draft text:
{draft}

Respond with a JSON object containing a "slides" array. Each slide should have:
{slide_format}

Example response format:
{example_format}
"""


class Stage1Service:
    """Service for Stage 1: Draft to Slide texts transformation."""

    async def generate_slide_texts(
        self,
        session_id: str,
        draft_text: str,
        num_slides: int = 5,
        include_titles: bool = True,
        additional_instructions: Optional[str] = None,
    ) -> Optional[SessionState]:
        """Generate slide texts from a draft."""
        session = session_manager.get_session(session_id)
        if not session:
            session = session_manager.create_session(session_id)

        # Store inputs
        session.draft_text = draft_text
        session.num_slides = num_slides
        session.include_titles = include_titles
        session.additional_instructions = additional_instructions

        # Build prompt
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

        example_format = (
            '{"slides": [{"title": "Hook", "body": "Grab attention here"}, ...]}'
            if include_titles
            else '{"slides": [{"body": "First slide content"}, ...]}'
        )

        additional = (
            f"Additional instructions: {additional_instructions}"
            if additional_instructions
            else ""
        )

        prompt = SLIDE_GENERATION_PROMPT.format(
            num_slides=num_slides,
            title_instruction=title_instruction,
            additional_instructions=additional,
            draft=draft_text,
            slide_format=slide_format,
            example_format=example_format,
        )

        # Generate with Gemini
        result = await gemini_service.generate_json(prompt)

        # Parse and store slides
        slides_data = result.get("slides", [])
        session.slides = []

        for i, slide_data in enumerate(slides_data[:num_slides]):
            slide = Slide(
                index=i,
                text=SlideText(
                    title=slide_data.get("title") if include_titles else None,
                    body=slide_data.get("body", ""),
                ),
            )
            session.slides.append(slide)

        # Ensure we have the requested number of slides
        while len(session.slides) < num_slides:
            session.slides.append(
                Slide(
                    index=len(session.slides),
                    text=SlideText(body=f"Slide {len(session.slides) + 1} content"),
                )
            )

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
        )

    async def regenerate_slide_text(
        self,
        session_id: str,
        slide_index: int,
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

        prompt = f"""Rewrite slide {slide_index + 1} of {len(session.slides)} for a carousel.

Original draft context: {session.draft_text[:500]}...

{prev_context}
{next_context}

Current slide to rewrite: {session.slides[slide_index].text.get_full_text()}

Create a fresh take on this slide that:
1. Maintains the core message
2. Flows well with surrounding slides
3. Uses engaging language

{"Include both title and body." if session.include_titles else "Only provide body text."}

Respond with JSON:
{{"title": "...", "body": "..."}}
"""

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
