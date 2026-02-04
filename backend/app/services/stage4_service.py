"""Stage 4 service - Typography/layout rendering."""

import logging
from typing import Optional, Dict, Any

from app.models.session import SessionState
from app.models.style import TextStyle, BoxStyle, StrokeStyle, ShadowStyle
from app.services.rendering_service import rendering_service
from app.services.gemini_service import gemini_service
from app.services.session_manager import session_manager

logger = logging.getLogger(__name__)


STYLE_SUGGESTION_PROMPT = """You are an expert designer suggesting typography for a social media carousel slide.

Analyze the slide content and suggest appropriate text styling.

Slide text: {text}

Consider:
1. The message tone (professional, casual, urgent, inspirational)
2. Text length and readability
3. Standard social media carousel best practices

Suggest a style JSON with these properties:
- font_family: One of "Inter", "Roboto", "Montserrat", "Lato", "Oswald", "Poppins"
- font_weight: 400, 500, 600, or 700
- font_size_px: Between 48 and 96
- text_color: Hex color (e.g., "#FFFFFF")
- alignment: "left", "center", or "right"
- box:
  - x_pct: 0.0 to 1.0 (text box X position as percentage)
  - y_pct: 0.0 to 1.0 (text box Y position as percentage)
  - w_pct: 0.0 to 1.0 (text box width as percentage)
  - h_pct: 0.0 to 1.0 (text box height as percentage)
  - padding_pct: 0.0 to 0.2 (padding as percentage)
- line_spacing: 1.0 to 1.5
- stroke:
  - enabled: true/false
  - width_px: 0 to 4
  - color: Hex color
- shadow:
  - enabled: true/false
  - dx: -4 to 4
  - dy: -4 to 4
  - blur: 0 to 8
  - color: Hex color with alpha

Respond with valid JSON only.
"""


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

            # Get or generate style
            if use_ai_suggestions and not slide.style.font_size_px == 72:
                # Only suggest if using default style
                pass  # Keep existing style

            # Render text on image
            text = slide.text.get_full_text()
            if text.strip():
                slide.final_image = rendering_service.render_text_on_image(
                    background_base64=slide.image_data,
                    text=text,
                    style=slide.style,
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

        text = slide.text.get_full_text()
        if text.strip():
            slide.final_image = rendering_service.render_text_on_image(
                background_base64=slide.image_data,
                text=text,
                style=slide.style,
            )
        else:
            slide.final_image = slide.image_data

        session_manager.update_session(session)
        return session

    async def suggest_style(
        self,
        session_id: str,
        slide_index: int,
    ) -> Optional[SessionState]:
        """Use AI to suggest optimal style for a slide."""
        session = session_manager.get_session(session_id)
        if not session or slide_index >= len(session.slides):
            return None

        slide = session.slides[slide_index]
        text = slide.text.get_full_text()

        prompt = STYLE_SUGGESTION_PROMPT.format(text=text)
        result = await gemini_service.generate_json(prompt)

        if result:
            # Update style with AI suggestions
            slide.style = self._parse_style_json(result)
            session_manager.update_session(session)

        return session

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
        if "text_color" in style_updates:
            current_style.text_color = style_updates["text_color"]
        if "alignment" in style_updates:
            current_style.alignment = style_updates["alignment"]
        if "line_spacing" in style_updates:
            current_style.line_spacing = style_updates["line_spacing"]
        if "max_lines" in style_updates:
            current_style.max_lines = style_updates["max_lines"]

        # Update box properties
        if "box" in style_updates:
            box = style_updates["box"]
            if "x_pct" in box:
                current_style.box.x_pct = box["x_pct"]
            if "y_pct" in box:
                current_style.box.y_pct = box["y_pct"]
            if "w_pct" in box:
                current_style.box.w_pct = box["w_pct"]
            if "h_pct" in box:
                current_style.box.h_pct = box["h_pct"]
            if "padding_pct" in box:
                current_style.box.padding_pct = box["padding_pct"]

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

    def _parse_style_json(self, data: Dict[str, Any]) -> TextStyle:
        """Parse style JSON into TextStyle model."""
        box_data = data.get("box", {})
        stroke_data = data.get("stroke", {})
        shadow_data = data.get("shadow", {})

        return TextStyle(
            font_family=data.get("font_family", "Inter"),
            font_weight=data.get("font_weight", 700),
            font_size_px=data.get("font_size_px", 72),
            text_color=data.get("text_color", "#FFFFFF"),
            alignment=data.get("alignment", "center"),
            line_spacing=data.get("line_spacing", 1.2),
            max_lines=data.get("max_lines", 6),
            box=BoxStyle(
                x_pct=box_data.get("x_pct", 0.1),
                y_pct=box_data.get("y_pct", 0.2),
                w_pct=box_data.get("w_pct", 0.8),
                h_pct=box_data.get("h_pct", 0.5),
                padding_pct=box_data.get("padding_pct", 0.05),
            ),
            stroke=StrokeStyle(
                enabled=stroke_data.get("enabled", False),
                width_px=stroke_data.get("width_px", 2),
                color=stroke_data.get("color", "#000000"),
            ),
            shadow=ShadowStyle(
                enabled=shadow_data.get("enabled", False),
                dx=shadow_data.get("dx", 2),
                dy=shadow_data.get("dy", 2),
                blur=shadow_data.get("blur", 4),
                color=shadow_data.get("color", "#00000080"),
            ),
        )


# Global Stage 4 service instance
stage4_service = Stage4Service()
