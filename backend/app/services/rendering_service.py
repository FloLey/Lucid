"""Rendering service for typography and layout on images."""

import logging
from typing import List, Tuple, Optional, Union

from PIL import Image, ImageDraw, ImageFont

from app.models.style import TextStyle, BoxStyle
from app.services.font_manager import FontManager
from app.services.storage_service import StorageService
from app.services.config_manager import ConfigManager
from app.config import IMAGE_WIDTH, IMAGE_HEIGHT

logger = logging.getLogger(__name__)


class RenderingService:
    """Service for rendering text onto images with typography and layout."""

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        font_manager: Optional[FontManager] = None,
        storage_service: Optional[StorageService] = None,
    ):
        # Dependencies are provided via DI container
        self.config_manager = config_manager
        self.font_manager = font_manager
        self.storage_service = storage_service
        # Ensure dependencies are present (should always be true with DI container)
        if not all([self.config_manager, self.font_manager, self.storage_service]):
            raise ValueError("All dependencies must be provided to RenderingService")

    def _wrap_text(
        self,
        text: str,
        font: Union[ImageFont.FreeTypeFont, ImageFont.ImageFont],
        max_width: int,
        draw: ImageDraw.ImageDraw,
    ) -> List[str]:
        """Wrap text to fit within a given width."""
        words = text.split()
        lines: List[str] = []
        current_line: List[str] = []

        for word in words:
            test_line = " ".join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            line_width = bbox[2] - bbox[0]

            if line_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]

        if current_line:
            lines.append(" ".join(current_line))

        return lines if lines else [""]

    def _get_text_color(self, color: str) -> Tuple[int, int, int, int]:
        """Parse hex color to RGBA tuple."""
        color = color.lstrip("#")
        if len(color) == 6:
            r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
            return (r, g, b, 255)
        elif len(color) == 8:
            r, g, b, a = (
                int(color[0:2], 16),
                int(color[2:4], 16),
                int(color[4:6], 16),
                int(color[6:8], 16),
            )
            return (r, g, b, a)
        return (255, 255, 255, 255)

    def _draw_lines(
        self,
        draw: ImageDraw.ImageDraw,
        lines: List[str],
        font: Union[ImageFont.FreeTypeFont, ImageFont.ImageFont],
        style: TextStyle,
        line_height: float,
        start_y: float,
        box_x: int,
        box_w: int,
        padding: int,
        text_color: Tuple[int, int, int, int],
        stroke_color: Optional[Tuple[int, int, int, int]],
    ) -> None:
        """Draw lines of text with alignment, shadow, and stroke."""
        for i, line in enumerate(lines):
            line_y = int(start_y + (i * line_height))

            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]

            if style.alignment == "left":
                line_x = int(box_x + padding)
            elif style.alignment == "right":
                line_x = int(box_x + box_w - padding - line_width)
            else:  # center
                line_x = int(box_x + (box_w - line_width) / 2)

            # Draw shadow
            if style.shadow.enabled:
                shadow_color = self._get_text_color(style.shadow.color)
                draw.text(
                    (line_x + style.shadow.dx, line_y + style.shadow.dy),
                    line,
                    font=font,
                    fill=shadow_color,
                )

            # Draw text (with or without stroke)
            if style.stroke.enabled:
                draw.text(
                    (line_x, line_y),
                    line,
                    font=font,
                    fill=text_color,
                    stroke_width=style.stroke.width_px,
                    stroke_fill=stroke_color,
                )
            else:
                draw.text(
                    (line_x, line_y),
                    line,
                    font=font,
                    fill=text_color,
                )

    def _find_fitting_size(
        self,
        text: str,
        font_family: str,
        font_weight: int,
        max_size: int,
        line_spacing: float,
        box_width: int,
        box_height: int,
        draw: ImageDraw.ImageDraw,
    ) -> Tuple[int, List[str]]:
        """Find the largest font size (up to max_size) where all text fits."""
        if not self.font_manager:
            raise ValueError("Font manager not initialized")
        min_size = 12
        if max_size < min_size:
            max_size = min_size

        best_size = min_size
        best_lines: List[str] = []
        low, high = min_size, max_size

        while low <= high:
            mid = (low + high) // 2
            font = self.font_manager.get_font(font_family, font_weight, mid)
            lines = self._wrap_text(text, font, box_width, draw)

            total_h = mid * line_spacing * len(lines)
            if total_h <= box_height:
                best_size = mid
                best_lines = lines
                low = mid + 1
            else:
                high = mid - 1

        if not best_lines:
            font = self.font_manager.get_font(font_family, font_weight, min_size)
            best_lines = self._wrap_text(text, font, box_width, draw)
            best_size = min_size

        return best_size, best_lines

    def _render_text_block(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        style: TextStyle,
        box: BoxStyle,
        font_size_px: int,
        font_weight: int,
        text_color: Tuple[int, int, int, int],
        stroke_color: Optional[Tuple[int, int, int, int]],
    ) -> None:
        """Render a single text block within its box, auto-scaling to fit."""
        if not self.font_manager:
            raise ValueError("Font manager not initialized")
        padding = int(IMAGE_WIDTH * box.padding_pct)
        box_x = int(IMAGE_WIDTH * box.x_pct)
        box_y = int(IMAGE_HEIGHT * box.y_pct)
        box_w = int(IMAGE_WIDTH * box.w_pct)
        box_h = int(IMAGE_HEIGHT * box.h_pct)

        text_width = box_w - (2 * padding)
        text_height = box_h - (2 * padding)

        if text_width <= 0 or text_height <= 0:
            return

        font_size, lines = self._find_fitting_size(
            text,
            style.font_family,
            font_weight,
            font_size_px,
            style.line_spacing,
            text_width,
            text_height,
            draw,
        )

        font = self.font_manager.get_font(style.font_family, font_weight, font_size)
        line_height = font_size * style.line_spacing
        total_text_height = line_height * len(lines)
        start_y = box_y + padding + (text_height - total_text_height) / 2

        self._draw_lines(
            draw,
            lines,
            font,
            style,
            line_height,
            start_y,
            box_x,
            box_w,
            padding,
            text_color,
            stroke_color,
        )

    def render_text_on_image(
        self,
        background_base64: str,
        style: TextStyle,
        title: Optional[str] = None,
        body: str = "",
    ) -> str:
        """Render text onto a background image with given style.

        *background_base64* may be either a raw base64 PNG string or an
        ``/images/<uuid>.png`` path written by :meth:`StorageService.save_image_to_disk`.
        """
        if not self.storage_service:
            raise ValueError("Storage service not initialized")
        background = self.storage_service.decode_image_from_path_or_b64(background_base64)
        background = background.convert("RGBA")

        if background.size != (IMAGE_WIDTH, IMAGE_HEIGHT):
            background = background.resize(
                (IMAGE_WIDTH, IMAGE_HEIGHT), Image.Resampling.LANCZOS
            )

        if not style.text_enabled:
            return self.storage_service.encode_image(background)

        draw = ImageDraw.Draw(background)

        text_color = self._get_text_color(style.text_color)
        stroke_color = (
            self._get_text_color(style.stroke.color) if style.stroke.enabled else None
        )

        has_title = title and title.strip()
        has_body = body and body.strip()

        if has_title:
            assert title is not None
            self._render_text_block(
                draw,
                title,
                style,
                style.title_box,
                style.font_size_px,
                style.font_weight,
                text_color,
                stroke_color,
            )

        if has_body:
            body_weight = max(400, style.font_weight - 200)
            self._render_text_block(
                draw,
                body,
                style,
                style.body_box,
                style.body_font_size_px,
                body_weight,
                text_color,
                stroke_color,
            )

        return self.storage_service.encode_image(background)

    def suggest_style(
        self,
        background_base64: str,
        text: str,
    ) -> TextStyle:
        """Analyze background and suggest optimal text style.

        *background_base64* accepts the same formats as :meth:`render_text_on_image`.
        """
        if not self.storage_service:
            raise ValueError("Storage service not initialized")
        background = self.storage_service.decode_image_from_path_or_b64(background_base64)
        background = background.convert("RGB")

        width, height = background.size
        samples = []

        regions = [
            (width // 4, height // 3, 3 * width // 4, 2 * height // 3),
            (width // 4, height // 2, 3 * width // 4, 3 * height // 4),
        ]

        for region in regions:
            region_img = background.crop(region)
            pixels = list(region_img.getdata())
            avg_r = sum(p[0] for p in pixels) // len(pixels)
            avg_g = sum(p[1] for p in pixels) // len(pixels)
            avg_b = sum(p[2] for p in pixels) // len(pixels)
            samples.append((avg_r, avg_g, avg_b))

        avg_brightness = sum(
            0.299 * s[0] + 0.587 * s[1] + 0.114 * s[2] for s in samples
        ) / len(samples)

        if avg_brightness > 128:
            text_color = "#000000"
            stroke_enabled = True
            stroke_color = "#FFFFFF"
        else:
            text_color = "#FFFFFF"
            stroke_enabled = True
            stroke_color = "#000000"

        style = TextStyle(
            font_family="Inter",
            font_weight=700,
            font_size_px=64,
            body_font_size_px=40,
            text_color=text_color,
            alignment="center",
            line_spacing=1.3,
        )
        style.stroke.enabled = stroke_enabled
        style.stroke.width_px = 2
        style.stroke.color = stroke_color

        return style
