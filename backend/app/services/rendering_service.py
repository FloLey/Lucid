"""Rendering service for typography and layout on images."""

import logging
from io import BytesIO
from typing import List, Tuple, Optional

from PIL import Image, ImageDraw, ImageFilter

from app.models.style import TextStyle
from app.services.font_manager import font_manager
from app.services.image_service import image_service
from app.config import IMAGE_WIDTH, IMAGE_HEIGHT

logger = logging.getLogger(__name__)


class RenderingService:
    """Service for rendering text onto images with typography and layout."""

    def _wrap_text(
        self,
        text: str,
        font,
        max_width: int,
        draw: ImageDraw.ImageDraw,
    ) -> List[str]:
        """Wrap text to fit within a given width."""
        words = text.split()
        lines = []
        current_line = []

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
            r, g, b, a = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16), int(color[6:8], 16)
            return (r, g, b, a)
        return (255, 255, 255, 255)

    def _fits_dimensions(
        self,
        text: str,
        style: TextStyle,
        draw: ImageDraw.ImageDraw,
        font_size: int,
        box_width: int,
        box_height: int,
    ) -> Tuple[bool, List[str]]:
        """
        Check if text at given font size fits within dimensions.

        Returns (fits, lines) tuple.
        """
        font = font_manager.get_font(
            style.font_family,
            style.font_weight,
            font_size,
        )

        # Wrap text with current font size
        lines = self._wrap_text(text, font, box_width, draw)

        # Check if we exceed max lines
        if len(lines) > style.max_lines:
            lines = lines[:style.max_lines]
            lines[-1] = lines[-1].rstrip() + "..."

        # Calculate total text height
        line_height = font_size * style.line_spacing
        total_height = line_height * len(lines)

        fits = total_height <= box_height
        return fits, lines

    def _calculate_auto_font_size(
        self,
        text: str,
        style: TextStyle,
        draw: ImageDraw.ImageDraw,
        box_width: int,
        box_height: int,
    ) -> Tuple[int, List[str]]:
        """
        Calculate optimal font size using binary search algorithm.

        Binary search is O(log n) compared to linear O(n) approach.
        Guaranteed to find best fit in ~7 iterations (log2(128)).
        """
        min_size = 12
        max_size = style.font_size_px

        # Edge case: if max is less than min
        if max_size < min_size:
            max_size = min_size

        best_size = min_size
        best_lines: List[str] = []

        low = min_size
        high = max_size

        while low <= high:
            mid = (low + high) // 2
            fits, lines = self._fits_dimensions(
                text, style, draw, mid, box_width, box_height
            )

            if fits:
                # This size works, try larger
                best_size = mid
                best_lines = lines
                low = mid + 1
            else:
                # Too big, try smaller
                high = mid - 1

        # If no size worked, use minimum
        if not best_lines:
            _, best_lines = self._fits_dimensions(
                text, style, draw, min_size, box_width, box_height
            )
            best_size = min_size

        return best_size, best_lines

    def render_text_on_image(
        self,
        background_base64: str,
        text: str,
        style: TextStyle,
    ) -> str:
        """Render text onto a background image with given style."""
        # Decode background image
        background = image_service.decode_image(background_base64)
        background = background.convert("RGBA")

        # Ensure correct dimensions
        if background.size != (IMAGE_WIDTH, IMAGE_HEIGHT):
            background = background.resize((IMAGE_WIDTH, IMAGE_HEIGHT), Image.Resampling.LANCZOS)

        # Create drawing context
        draw = ImageDraw.Draw(background)

        # Calculate box dimensions
        padding = int(IMAGE_WIDTH * style.box.padding_pct)
        box_x = int(IMAGE_WIDTH * style.box.x_pct)
        box_y = int(IMAGE_HEIGHT * style.box.y_pct)
        box_w = int(IMAGE_WIDTH * style.box.w_pct)
        box_h = int(IMAGE_HEIGHT * style.box.h_pct)

        # Available space after padding
        text_width = box_w - (2 * padding)
        text_height = box_h - (2 * padding)

        # Auto-scale font and wrap text
        font_size, lines = self._calculate_auto_font_size(
            text, style, draw, text_width, text_height
        )

        # Get font
        font = font_manager.get_font(
            style.font_family,
            style.font_weight,
            font_size,
        )

        # Calculate vertical positioning
        line_height = font_size * style.line_spacing
        total_text_height = line_height * len(lines)
        start_y = box_y + padding + (text_height - total_text_height) / 2

        # Get colors
        text_color = self._get_text_color(style.text_color)
        stroke_color = self._get_text_color(style.stroke.color) if style.stroke.enabled else None

        # Render each line
        for i, line in enumerate(lines):
            # Calculate line position
            line_y = start_y + (i * line_height)

            # Calculate x position based on alignment
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]

            if style.alignment == "left":
                line_x = box_x + padding
            elif style.alignment == "right":
                line_x = box_x + box_w - padding - line_width
            else:  # center
                line_x = box_x + (box_w - line_width) / 2

            # Draw shadow if enabled
            if style.shadow.enabled:
                shadow_color = self._get_text_color(style.shadow.color)
                # Create shadow layer
                shadow_x = line_x + style.shadow.dx
                shadow_y = line_y + style.shadow.dy

                # Draw shadow text
                draw.text(
                    (shadow_x, shadow_y),
                    line,
                    font=font,
                    fill=shadow_color,
                )

            # Draw stroke if enabled
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

        # Convert back to base64
        return image_service.encode_image(background)

    def suggest_style(
        self,
        background_base64: str,
        text: str,
    ) -> TextStyle:
        """Analyze background and suggest optimal text style."""
        # Decode and analyze background
        background = image_service.decode_image(background_base64)
        background = background.convert("RGB")

        # Sample colors from different regions
        width, height = background.size
        samples = []

        # Sample from potential text areas (center and lower regions)
        regions = [
            (width // 4, height // 3, 3 * width // 4, 2 * height // 3),  # Center
            (width // 4, height // 2, 3 * width // 4, 3 * height // 4),  # Lower center
        ]

        for region in regions:
            region_img = background.crop(region)
            # Get average color of region
            pixels = list(region_img.getdata())
            avg_r = sum(p[0] for p in pixels) // len(pixels)
            avg_g = sum(p[1] for p in pixels) // len(pixels)
            avg_b = sum(p[2] for p in pixels) // len(pixels)
            samples.append((avg_r, avg_g, avg_b))

        # Calculate average brightness
        avg_brightness = sum(
            0.299 * s[0] + 0.587 * s[1] + 0.114 * s[2]
            for s in samples
        ) / len(samples)

        # Choose text color based on background brightness
        if avg_brightness > 128:
            text_color = "#000000"
            stroke_enabled = True
            stroke_color = "#FFFFFF"
        else:
            text_color = "#FFFFFF"
            stroke_enabled = True
            stroke_color = "#000000"

        # Create style suggestion
        style = TextStyle(
            font_family="Inter",
            font_weight=700,
            font_size_px=64,
            text_color=text_color,
            alignment="center",
            line_spacing=1.3,
        )
        style.stroke.enabled = stroke_enabled
        style.stroke.width_px = 2
        style.stroke.color = stroke_color

        return style


# Global rendering service instance
rendering_service = RenderingService()
