"""Tests for RenderingService — color parsing, text wrapping, font fitting."""

import pytest
from PIL import Image, ImageDraw, ImageFont
from unittest.mock import MagicMock

from app.dependencies import container
from app.services.rendering_service import RenderingService, _MIN_FONT_SIZE


rendering_service = container.rendering_service


class TestGetTextColor:
    """Tests for RenderingService._get_text_color()."""

    def test_valid_6_char_hex(self):
        """Standard 6-char hex string returns correct RGBA with alpha=255."""
        assert rendering_service._get_text_color("#FF0000") == (255, 0, 0, 255)
        assert rendering_service._get_text_color("#000000") == (0, 0, 0, 255)
        assert rendering_service._get_text_color("#FFFFFF") == (255, 255, 255, 255)

    def test_valid_8_char_hex_with_alpha(self):
        """8-char hex string correctly parses the alpha channel."""
        r, g, b, a = rendering_service._get_text_color("#FF000080")
        assert (r, g, b) == (255, 0, 0)
        assert a == 128

    def test_lowercase_hex(self):
        """Lowercase hex digits are parsed correctly."""
        assert rendering_service._get_text_color("#ff8800") == (255, 136, 0, 255)

    def test_no_hash_prefix_falls_back_to_white(self):
        """A hex string without '#' that is not 6 or 8 chars falls back to white."""
        # "abc" is 3 chars — neither 6 nor 8 — falls back
        result = rendering_service._get_text_color("abc")
        assert result == (255, 255, 255, 255)

    def test_invalid_hex_chars_fall_back_to_white(self):
        """Non-hex characters (e.g. 'G') trigger the ValueError fallback → white."""
        result = rendering_service._get_text_color("#GGGGGG")
        assert result == (255, 255, 255, 255)

    def test_invalid_8_char_hex_falls_back_to_white(self):
        """Invalid 8-char hex also falls back to white."""
        result = rendering_service._get_text_color("#GGGGGGGG")
        assert result == (255, 255, 255, 255)


class TestWrapText:
    """Tests for RenderingService._wrap_text()."""

    def _make_draw(self) -> ImageDraw.ImageDraw:
        img = Image.new("RGBA", (100, 100))
        return ImageDraw.Draw(img)

    def _default_font(self) -> ImageFont.ImageFont:
        return ImageFont.load_default()

    def test_empty_string_returns_single_empty_line(self):
        """Empty text should return ['']."""
        draw = self._make_draw()
        font = self._default_font()
        lines = rendering_service._wrap_text("", font, 200, draw)
        assert lines == [""]

    def test_short_text_fits_on_one_line(self):
        """Text narrower than max_width stays on a single line."""
        draw = self._make_draw()
        font = self._default_font()
        lines = rendering_service._wrap_text("Hi", font, 1000, draw)
        assert len(lines) == 1
        assert lines[0] == "Hi"

    def test_long_text_wraps_across_lines(self):
        """Text wider than max_width is split into multiple lines."""
        draw = self._make_draw()
        font = self._default_font()
        # Very narrow width (5px) forces each word onto its own line
        text = "one two three"
        lines = rendering_service._wrap_text(text, font, 5, draw)
        assert len(lines) > 1

    def test_whitespace_only_returns_empty_line(self):
        """Whitespace-only string splits to nothing and returns ['']."""
        draw = self._make_draw()
        font = self._default_font()
        lines = rendering_service._wrap_text("   ", font, 200, draw)
        assert lines == [""]


class TestFindFittingSize:
    """Tests for RenderingService._find_fitting_size()."""

    def _make_draw(self) -> ImageDraw.ImageDraw:
        img = Image.new("RGBA", (1080, 1350))
        return ImageDraw.Draw(img)

    def test_returns_size_within_bounds(self):
        """Returned size must be between _MIN_FONT_SIZE and max_size."""
        draw = self._make_draw()
        size, lines = rendering_service._find_fitting_size(
            text="Hello world",
            font_family="Inter",
            font_weight=400,
            max_size=80,
            line_spacing=1.2,
            box_width=800,
            box_height=200,
            draw=draw,
        )
        assert _MIN_FONT_SIZE <= size <= 80
        assert len(lines) > 0

    def test_large_text_returns_min_size(self):
        """Very large text that can't fit even at min size still returns min size."""
        draw = self._make_draw()
        # Tiny box — text can only fit at minimum size at best
        size, lines = rendering_service._find_fitting_size(
            # 200 space-separated words in a 1px box: at no font size do they all
            # fit, so the binary search finds no candidate → min-size fallback.
            text=" ".join(["w"] * 200),
            font_family="Inter",
            font_weight=400,
            max_size=200,
            line_spacing=1.2,
            box_width=1,
            box_height=1,
            draw=draw,
        )
        assert size == _MIN_FONT_SIZE
        assert len(lines) > 0

    def test_max_size_smaller_than_min_size_is_clamped(self):
        """If max_size < _MIN_FONT_SIZE, it is clamped up to _MIN_FONT_SIZE."""
        draw = self._make_draw()
        size, _ = rendering_service._find_fitting_size(
            text="Hi",
            font_family="Inter",
            font_weight=400,
            max_size=5,  # below minimum
            line_spacing=1.2,
            box_width=500,
            box_height=100,
            draw=draw,
        )
        assert size == _MIN_FONT_SIZE
