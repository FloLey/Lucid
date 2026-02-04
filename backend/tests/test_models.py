"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from app.models.style import TextStyle, BoxStyle, StrokeStyle, ShadowStyle
from app.models.slide import Slide, SlideText
from app.models.session import SessionState


class TestBoxStyle:
    """Tests for BoxStyle model."""

    def test_default_values(self):
        """Test default box style values."""
        box = BoxStyle()
        assert box.x_pct == 0.1
        assert box.y_pct == 0.2
        assert box.w_pct == 0.8
        assert box.h_pct == 0.5
        assert box.padding_pct == 0.05

    def test_custom_values(self):
        """Test custom box style values."""
        box = BoxStyle(x_pct=0.5, y_pct=0.5, w_pct=0.5, h_pct=0.3)
        assert box.x_pct == 0.5
        assert box.y_pct == 0.5

    def test_validation_bounds(self):
        """Test percentage bounds validation."""
        with pytest.raises(ValidationError):
            BoxStyle(x_pct=1.5)  # Over 1
        with pytest.raises(ValidationError):
            BoxStyle(y_pct=-0.1)  # Under 0


class TestStrokeStyle:
    """Tests for StrokeStyle model."""

    def test_defaults(self):
        """Test default stroke settings."""
        stroke = StrokeStyle()
        assert stroke.enabled is False
        assert stroke.width_px == 2
        assert stroke.color == "#000000"

    def test_enabled_stroke(self):
        """Test enabled stroke with custom settings."""
        stroke = StrokeStyle(enabled=True, width_px=4, color="#FF0000")
        assert stroke.enabled is True
        assert stroke.width_px == 4
        assert stroke.color == "#FF0000"


class TestShadowStyle:
    """Tests for ShadowStyle model."""

    def test_defaults(self):
        """Test default shadow settings."""
        shadow = ShadowStyle()
        assert shadow.enabled is False
        assert shadow.dx == 2
        assert shadow.dy == 2
        assert shadow.blur == 4

    def test_enabled_shadow(self):
        """Test enabled shadow with custom settings."""
        shadow = ShadowStyle(enabled=True, dx=4, dy=4, blur=8, color="#00000099")
        assert shadow.enabled is True
        assert shadow.blur == 8


class TestTextStyle:
    """Tests for TextStyle model."""

    def test_defaults(self):
        """Test default text style."""
        style = TextStyle()
        assert style.font_family == "Inter"
        assert style.font_weight == 700
        assert style.font_size_px == 72
        assert style.text_color == "#FFFFFF"
        assert style.alignment == "center"
        assert style.line_spacing == 1.2

    def test_custom_style(self):
        """Test custom text style."""
        style = TextStyle(
            font_family="Roboto",
            font_size_px=48,
            alignment="left",
            text_color="#000000",
        )
        assert style.font_family == "Roboto"
        assert style.font_size_px == 48
        assert style.alignment == "left"

    def test_nested_styles(self):
        """Test nested box, stroke, shadow styles."""
        style = TextStyle(
            box=BoxStyle(x_pct=0.2, y_pct=0.3),
            stroke=StrokeStyle(enabled=True, width_px=3),
            shadow=ShadowStyle(enabled=True),
        )
        assert style.box.x_pct == 0.2
        assert style.stroke.enabled is True
        assert style.shadow.enabled is True


class TestSlideText:
    """Tests for SlideText model."""

    def test_body_only(self):
        """Test slide with body only."""
        text = SlideText(body="Hello world")
        assert text.title is None
        assert text.body == "Hello world"
        assert text.get_full_text() == "Hello world"

    def test_with_title(self):
        """Test slide with title and body."""
        text = SlideText(title="Welcome", body="This is the content")
        assert text.title == "Welcome"
        assert "Welcome" in text.get_full_text()
        assert "This is the content" in text.get_full_text()


class TestSlide:
    """Tests for Slide model."""

    def test_default_slide(self):
        """Test default slide values."""
        slide = Slide(index=0)
        assert slide.index == 0
        assert slide.image_prompt is None
        assert slide.image_data is None
        assert slide.final_image is None

    def test_complete_slide(self):
        """Test slide with all data."""
        slide = Slide(
            index=2,
            text=SlideText(title="Slide 3", body="Content here"),
            image_prompt="A beautiful sunset",
            style=TextStyle(font_size_px=60),
        )
        assert slide.index == 2
        assert slide.text.title == "Slide 3"
        assert slide.image_prompt == "A beautiful sunset"
        assert slide.style.font_size_px == 60


class TestSessionState:
    """Tests for SessionState model."""

    def test_new_session(self):
        """Test creating a new session."""
        session = SessionState(session_id="test-123")
        assert session.session_id == "test-123"
        assert session.current_stage == 1
        assert session.num_slides == 5
        assert session.include_titles is True
        assert len(session.slides) == 0

    def test_session_with_slides(self):
        """Test session with slides."""
        session = SessionState(session_id="test-456")
        session.ensure_slides(3)
        assert len(session.slides) == 3
        assert session.slides[0].index == 0
        assert session.slides[2].index == 2

    def test_get_slide(self):
        """Test getting a slide by index."""
        session = SessionState(session_id="test-789")
        session.ensure_slides(5)
        slide = session.get_slide(2)
        assert slide is not None
        assert slide.index == 2

        # Out of bounds
        assert session.get_slide(10) is None
        assert session.get_slide(-1) is None

    def test_update_timestamp(self):
        """Test timestamp update."""
        session = SessionState(session_id="test-ts")
        old_time = session.updated_at
        import time
        time.sleep(0.01)
        session.update_timestamp()
        assert session.updated_at > old_time
