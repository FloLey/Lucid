"""Stage 3 service - Image prompts to Images transformation."""

import asyncio
import logging
from typing import Optional

from app.models.session import SessionState
from app.services.image_service import image_service
from app.services.session_manager import session_manager

logger = logging.getLogger(__name__)


class Stage3Service:
    """Service for Stage 3: Image prompts to Images transformation."""

    async def generate_all_images(
        self,
        session_id: str,
    ) -> Optional[SessionState]:
        """Generate images for all slides."""
        session = session_manager.get_session(session_id)
        if not session or not session.slides:
            return None

        # Check if all slides have prompts
        for slide in session.slides:
            if not slide.image_prompt:
                # Use a default prompt if not set
                slide.image_prompt = f"Abstract professional background for slide {slide.index + 1}"

        # Generate images for all slides in parallel
        shared_prefix = session.shared_prompt_prefix or ""

        full_prompts = [
            f"{shared_prefix} {slide.image_prompt}".strip()
            for slide in session.slides
        ]
        results = await asyncio.gather(
            *(image_service.generate_image(prompt) for prompt in full_prompts)
        )
        for slide, image_data in zip(session.slides, results):
            slide.image_data = image_data

        session_manager.update_session(session)
        return session

    async def regenerate_image(
        self,
        session_id: str,
        slide_index: int,
    ) -> Optional[SessionState]:
        """Regenerate image for a single slide."""
        session = session_manager.get_session(session_id)
        if not session or slide_index >= len(session.slides):
            return None

        slide = session.slides[slide_index]
        if not slide.image_prompt:
            slide.image_prompt = f"Abstract professional background for slide {slide_index + 1}"

        shared_prefix = session.shared_prompt_prefix or ""
        full_prompt = f"{shared_prefix} {slide.image_prompt}".strip()

        slide.image_data = await image_service.generate_image(full_prompt)

        session_manager.update_session(session)
        return session

    def set_image_data(
        self,
        session_id: str,
        slide_index: int,
        image_data: str,
    ) -> Optional[SessionState]:
        """Set image data directly (for uploads)."""
        session = session_manager.get_session(session_id)
        if not session or slide_index >= len(session.slides):
            return None

        session.slides[slide_index].image_data = image_data
        session_manager.update_session(session)
        return session


# Global Stage 3 service instance
stage3_service = Stage3Service()
