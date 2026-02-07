"""Stage 4 service - Typography/layout rendering."""

import logging
from typing import Optional, Dict, Any

from app.models.session import SessionState
from app.models.style import BoxStyle
from app.services.rendering_service import rendering_service
from app.services.session_manager import session_manager

logger = logging.getLogger(__name__)


class Stage4Service:
    """Service for Stage 4: Typography/layout rendering."""

    async def apply_text_to_all_images(
        self,
        session_id: str,
        use_ai_suggestions: bool = True,
    ) -> Optional[SessionState]:
        """Apply text styling to all slide images."""
        session = session_manager.get_session(session_id)
        if not session or not session.slides:
            return None

        for slide in session.slides:
            if not slide.image_data:
                continue

            # Render text on image
            if slide.text.title or slide.text.body.strip():
                slide.final_image = rendering_service.render_text_on_image(
                    background_base64=slide.image_data,
                    style=slide.style,
                    title=slide.text.title,
                    body=slide.text.body,
                )
            else:
                # No text, just copy the background
                slide.final_image = slide.image_data

        session_manager.update_session(session)
        return session

    async def apply_text_to_image(
        self,
        session_id: str,
        slide_index: int,
    ) -> Optional[SessionState]:
        """Apply text styling to a single slide image."""
        session = session_manager.get_session(session_id)
        if not session or slide_index >= len(session.slides):
            return None

        slide = session.slides[slide_index]
        if not slide.image_data:
            return session

        if slide.text.title or slide.text.body.strip():
            slide.final_image = rendering_service.render_text_on_image(
                background_base64=slide.image_data,
                style=slide.style,
                title=slide.text.title,
                body=slide.text.body,
            )
        else:
            slide.final_image = slide.image_data

        session_manager.update_session(session)
        return session

    def _update_box(self, box: BoxStyle, data: Dict[str, Any]) -> None:
        """Update a BoxStyle from a dict of updates."""
        if "x_pct" in data:
            box.x_pct = data["x_pct"]
        if "y_pct" in data:
            box.y_pct = data["y_pct"]
        if "w_pct" in data:
            box.w_pct = data["w_pct"]
        if "h_pct" in data:
            box.h_pct = data["h_pct"]
        if "padding_pct" in data:
            box.padding_pct = data["padding_pct"]

    def update_style(
        self,
        session_id: str,
        slide_index: int,
        style_updates: Dict[str, Any],
    ) -> Optional[SessionState]:
        """Update style properties for a slide."""
        session = session_manager.get_session(session_id)
        if not session or slide_index >= len(session.slides):
            return None

        slide = session.slides[slide_index]
        current_style = slide.style

        # Update basic properties
        if "font_family" in style_updates:
            current_style.font_family = style_updates["font_family"]
        if "font_weight" in style_updates:
            current_style.font_weight = style_updates["font_weight"]
        if "font_size_px" in style_updates:
            current_style.font_size_px = style_updates["font_size_px"]
        if "body_font_size_px" in style_updates:
            current_style.body_font_size_px = style_updates["body_font_size_px"]
        if "text_color" in style_updates:
            current_style.text_color = style_updates["text_color"]
        if "alignment" in style_updates:
            current_style.alignment = style_updates["alignment"]
        if "line_spacing" in style_updates:
            current_style.line_spacing = style_updates["line_spacing"]
        if "max_lines" in style_updates:
            current_style.max_lines = style_updates["max_lines"]

        # Update title_box properties
        if "title_box" in style_updates:
            self._update_box(current_style.title_box, style_updates["title_box"])

        # Update body_box properties
        if "body_box" in style_updates:
            self._update_box(current_style.body_box, style_updates["body_box"])

        # Update stroke properties
        if "stroke" in style_updates:
            stroke = style_updates["stroke"]
            if "enabled" in stroke:
                current_style.stroke.enabled = stroke["enabled"]
            if "width_px" in stroke:
                current_style.stroke.width_px = stroke["width_px"]
            if "color" in stroke:
                current_style.stroke.color = stroke["color"]

        # Update shadow properties
        if "shadow" in style_updates:
            shadow = style_updates["shadow"]
            if "enabled" in shadow:
                current_style.shadow.enabled = shadow["enabled"]
            if "dx" in shadow:
                current_style.shadow.dx = shadow["dx"]
            if "dy" in shadow:
                current_style.shadow.dy = shadow["dy"]
            if "blur" in shadow:
                current_style.shadow.blur = shadow["blur"]
            if "color" in shadow:
                current_style.shadow.color = shadow["color"]

        session_manager.update_session(session)
        return session

    def apply_style_to_all(
        self,
        session_id: str,
        style_updates: Dict[str, Any],
    ) -> Optional[SessionState]:
        """Apply style updates to all slides."""
        session = session_manager.get_session(session_id)
        if not session or not session.slides:
            return None

        for i in range(len(session.slides)):
            self.update_style(session_id, i, style_updates)

        return session_manager.get_session(session_id)

    async def suggest_style(
        self,
        session_id: str,
        slide_index: int,
    ) -> Optional[SessionState]:
        """Use image analysis to suggest optimal style for a slide."""
        session = session_manager.get_session(session_id)
        if not session or slide_index >= len(session.slides):
            return None

        slide = session.slides[slide_index]
        if slide.image_data:
            suggested = rendering_service.suggest_style(slide.image_data, slide.text.body)
            slide.style = suggested
            session_manager.update_session(session)

        return session


# Global Stage 4 service instance
stage4_service = Stage4Service()
