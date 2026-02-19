"""Stage 4 service - Typography/layout rendering."""

from __future__ import annotations
import logging
from typing import Optional, Dict, Any, TYPE_CHECKING

from app.models.session import SessionState
from app.models.style import TextStyle

if TYPE_CHECKING:
    from app.services.rendering_service import RenderingService
    from app.services.session_manager import SessionManager

logger = logging.getLogger(__name__)


class Stage4Service:
    """Service for Stage 4: Typography/layout rendering."""

    session_manager: SessionManager
    rendering_service: RenderingService

    def __init__(
        self,
        session_manager: Optional[SessionManager] = None,
        rendering_service: Optional[RenderingService] = None,
    ):
        # Validate dependencies before assignment
        if not session_manager or not rendering_service:
            raise ValueError("All dependencies must be provided to Stage4Service")

        self.session_manager = session_manager
        self.rendering_service = rendering_service

    async def apply_text_to_all_images(
        self,
        session_id: str,
        use_ai_suggestions: bool = True,
    ) -> Optional[SessionState]:
        """Apply text styling to all slide images."""
        session = await self.session_manager.get_session(session_id)
        if not session or not session.slides:
            return None

        for slide in session.slides:
            if not slide.image_data:
                continue

            # Render text on image
            if slide.text.title or slide.text.body.strip():
                slide.final_image = self.rendering_service.render_text_on_image(
                    background_base64=slide.image_data,
                    style=slide.style,
                    title=slide.text.title,
                    body=slide.text.body,
                )
            else:
                # No text, just copy the background
                slide.final_image = slide.image_data

        await self.session_manager.update_session(session)
        return session

    async def apply_text_to_image(
        self,
        session_id: str,
        slide_index: int,
    ) -> Optional[SessionState]:
        """Apply text styling to a single slide image."""
        session = await self.session_manager.get_session(session_id)
        if not session or slide_index >= len(session.slides):
            return None

        slide = session.slides[slide_index]
        if not slide.image_data:
            return session

        if slide.text.title or slide.text.body.strip():
            slide.final_image = self.rendering_service.render_text_on_image(
                background_base64=slide.image_data,
                style=slide.style,
                title=slide.text.title,
                body=slide.text.body,
            )
        else:
            slide.final_image = slide.image_data

        await self.session_manager.update_session(session)
        return session

    def _deep_merge_style(self, style: TextStyle, updates: Dict[str, Any]) -> TextStyle:
        """Merge partial updates into a TextStyle, handling nested sub-models."""
        current = style.model_dump()
        for key, value in updates.items():
            if (
                key in current
                and isinstance(current[key], dict)
                and isinstance(value, dict)
            ):
                current[key] = {**current[key], **value}
            else:
                current[key] = value
        return TextStyle(**current)

    async def update_style(
        self,
        session_id: str,
        slide_index: int,
        style_updates: Dict[str, Any],
    ) -> Optional[SessionState]:
        """Update style properties for a slide."""
        session = await self.session_manager.get_session(session_id)
        if not session or slide_index >= len(session.slides):
            return None

        slide = session.slides[slide_index]
        slide.style = self._deep_merge_style(slide.style, style_updates)

        await self.session_manager.update_session(session)
        return session

    async def apply_style_to_all(
        self,
        session_id: str,
        style_updates: Dict[str, Any],
    ) -> Optional[SessionState]:
        """Apply style updates to all slides."""
        session = await self.session_manager.get_session(session_id)
        if not session or not session.slides:
            return None

        for slide in session.slides:
            slide.style = self._deep_merge_style(slide.style, style_updates)

        await self.session_manager.update_session(session)
        return session

    async def suggest_style(
        self,
        session_id: str,
        slide_index: int,
    ) -> Optional[SessionState]:
        """Use image analysis to suggest optimal style for a slide."""
        session = await self.session_manager.get_session(session_id)
        if not session or slide_index >= len(session.slides):
            return None

        slide = session.slides[slide_index]
        if slide.image_data:
            suggested = self.rendering_service.suggest_style(
                slide.image_data, slide.text.body
            )
            slide.style = suggested
            await self.session_manager.update_session(session)

        return session
