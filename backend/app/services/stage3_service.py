"""Stage 3 service - Image prompts to Images transformation."""

from __future__ import annotations
import asyncio
import logging
from typing import Optional, TYPE_CHECKING

from app.models.session import SessionState

if TYPE_CHECKING:
    from app.services.session_manager import SessionManager
    from app.services.image_service import ImageService

logger = logging.getLogger(__name__)


class Stage3Service:
    """Service for Stage 3: Image prompts to Images transformation."""

    session_manager: SessionManager
    image_service: ImageService

    def __init__(
        self,
        session_manager: Optional[SessionManager] = None,
        image_service: Optional[ImageService] = None,
    ):
        # Validate dependencies before assignment
        if not session_manager:
            raise ValueError("session_manager dependency is required")
        if not image_service:
            raise ValueError("image_service dependency is required")

        self.session_manager = session_manager
        self.image_service = image_service

    def _build_full_prompt(self, session: SessionState, slide_index: int) -> str:
        """Combine the session's shared visual theme with slide-specific details."""
        shared_prefix = session.shared_prompt_prefix or ""
        return f"{shared_prefix} {session.slides[slide_index].image_prompt}".strip()

    async def generate_all_images(
        self,
        session_id: str,
    ) -> Optional[SessionState]:
        """Generate images for all slides."""
        session = await self.session_manager.get_session(session_id)
        if not session or not session.slides:
            return None

        # Check if all slides have prompts
        for slide in session.slides:
            if not slide.image_prompt:
                # Use a default prompt if not set
                slide.image_prompt = (
                    f"Abstract professional background for slide {slide.index + 1}"
                )

        # Generate images for all slides in parallel
        full_prompts = [
            self._build_full_prompt(session, i) for i in range(len(session.slides))
        ]
        results = await asyncio.gather(
            *(self.image_service.generate_image(prompt) for prompt in full_prompts)
        )
        for slide, image_data in zip(session.slides, results):
            slide.image_data = image_data

        await self.session_manager.update_session(session)
        return session

    async def regenerate_image(
        self,
        session_id: str,
        slide_index: int,
    ) -> Optional[SessionState]:
        """Regenerate image for a single slide."""
        session = await self.session_manager.get_session(session_id)
        if not session or slide_index >= len(session.slides):
            return None

        slide = session.slides[slide_index]
        if not slide.image_prompt:
            slide.image_prompt = (
                f"Abstract professional background for slide {slide_index + 1}"
            )

        full_prompt = self._build_full_prompt(session, slide_index)
        slide.image_data = await self.image_service.generate_image(full_prompt)

        await self.session_manager.update_session(session)
        return session

    async def set_image_data(
        self,
        session_id: str,
        slide_index: int,
        image_data: str,
    ) -> Optional[SessionState]:
        """Set image data directly (for uploads)."""
        session = await self.session_manager.get_session(session_id)
        if not session or slide_index >= len(session.slides):
            return None

        session.slides[slide_index].image_data = image_data
        await self.session_manager.update_session(session)
        return session
