"""Tests for Stage 4 - Typography/Layout rendering."""

import asyncio
import base64
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.services.session_manager import session_manager
from app.services.stage4_service import stage4_service
from app.services.rendering_service import rendering_service
from app.services.image_service import image_service
from app.models.slide import Slide, SlideText
from app.models.style import TextStyle


@pytest.fixture
def client():
    """Create a test client."""
    session_manager.clear_all()
    return TestClient(app)


@pytest.fixture
def sample_image_base64():
    """Create a sample background image."""
    return image_service._generate_placeholder("Test background")


@pytest.fixture
def session_with_images(sample_image_base64):
    """Create a session with background images."""
    session_manager.clear_all()
    session = session_manager.create_session("test-stage4")
    session.slides = [
        Slide(
            index=0,
            text=SlideText(title="Welcome", body="Let's get started!"),
            image_data=sample_image_base64,
        ),
        Slide(
            index=1,
            text=SlideText(title="Key Point", body="This is the main idea."),
            image_data=sample_image_base64,
        ),
        Slide(
            index=2,
            text=SlideText(title="Conclusion", body="Take action now!"),
            image_data=sample_image_base64,
        ),
    ]
    session_manager.update_session(session)
    return session


@pytest.fixture
def mock_gemini():
    """Mock the Gemini service."""
    async def mock_generate_json(*args, **kwargs):
        return {
            "font_family": "Montserrat",
            "font_weight": 700,
            "font_size_px": 64,
            "text_color": "#FFFFFF",
            "alignment": "center",
            "title_box": {
                "x_pct": 0.1,
                "y_pct": 0.3,
                "w_pct": 0.8,
                "h_pct": 0.4,
            },
            "stroke": {"enabled": True, "width_px": 2, "color": "#000000"},
        }

    with patch("app.services.stage4_service.gemini_service") as mock:
        mock.generate_json = mock_generate_json
        yield mock


class TestRenderingService:
    """Tests for RenderingService."""

    def test_wrap_text_single_line(self, sample_image_base64):
        """Test text wrapping for single line."""
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (1080, 1350))
        draw = ImageDraw.Draw(img)
        font = font_manager_import().get_font("Inter", 700, 48)

        lines = rendering_service._wrap_text("Short text", font, 800, draw)
        assert len(lines) == 1
        assert lines[0] == "Short text"

    def test_wrap_text_multi_line(self, sample_image_base64):
        """Test text wrapping for multiple lines."""
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (1080, 1350))
        draw = ImageDraw.Draw(img)
        font = font_manager_import().get_font("Inter", 700, 48)

        long_text = "This is a much longer piece of text that should wrap to multiple lines when rendered"
        lines = rendering_service._wrap_text(long_text, font, 400, draw)
        assert len(lines) > 1

    def test_get_text_color_hex6(self):
        """Test parsing 6-character hex color."""
        color = rendering_service._get_text_color("#FF5500")
        assert color == (255, 85, 0, 255)

    def test_get_text_color_hex8(self):
        """Test parsing 8-character hex color with alpha."""
        color = rendering_service._get_text_color("#FF550080")
        assert color == (255, 85, 0, 128)

    def test_render_text_on_image(self, sample_image_base64):
        """Test basic text rendering."""
        style = TextStyle(
            font_family="Inter",
            font_size_px=48,
            text_color="#FFFFFF",
        )

        result = rendering_service.render_text_on_image(
            background_base64=sample_image_base64,
            text="Hello World",
            style=style,
        )

        assert result is not None
        # Should be valid base64 PNG
        decoded = base64.b64decode(result)
        assert decoded[:8] == b"\x89PNG\r\n\x1a\n"

    def test_render_with_stroke(self, sample_image_base64):
        """Test rendering with stroke enabled."""
        style = TextStyle(
            font_family="Inter",
            font_size_px=48,
            text_color="#FFFFFF",
        )
        style.stroke.enabled = True
        style.stroke.width_px = 3
        style.stroke.color = "#000000"

        result = rendering_service.render_text_on_image(
            background_base64=sample_image_base64,
            text="Stroked Text",
            style=style,
        )

        assert result is not None

    def test_render_with_shadow(self, sample_image_base64):
        """Test rendering with shadow enabled."""
        style = TextStyle(
            font_family="Inter",
            font_size_px=48,
            text_color="#FFFFFF",
        )
        style.shadow.enabled = True
        style.shadow.dx = 3
        style.shadow.dy = 3

        result = rendering_service.render_text_on_image(
            background_base64=sample_image_base64,
            text="Shadow Text",
            style=style,
        )

        assert result is not None

    def test_suggest_style(self, sample_image_base64):
        """Test style suggestion based on background."""
        style = rendering_service.suggest_style(
            background_base64=sample_image_base64,
            text="Test content",
        )

        assert style is not None
        assert style.font_family in ["Inter", "Roboto", "Montserrat"]
        assert style.text_color in ["#FFFFFF", "#000000"]


class TestStage4Service:
    """Tests for Stage4Service."""

    def test_apply_text_to_all_images(self, session_with_images):
        """Test applying text to all images."""
        session = asyncio.get_event_loop().run_until_complete(
            stage4_service.apply_text_to_all_images(session_id="test-stage4")
        )
        assert session is not None
        for slide in session.slides:
            assert slide.final_image is not None

    def test_apply_text_to_single_image(self, session_with_images):
        """Test applying text to a single image."""
        session = asyncio.get_event_loop().run_until_complete(
            stage4_service.apply_text_to_image(
                session_id="test-stage4",
                slide_index=1,
            )
        )
        assert session is not None
        assert session.slides[1].final_image is not None

    def test_apply_text_no_session(self):
        """Test applying text with no session."""
        session_manager.clear_all()
        session = asyncio.get_event_loop().run_until_complete(
            stage4_service.apply_text_to_all_images(session_id="nonexistent")
        )
        assert session is None

    def test_update_style(self, session_with_images):
        """Test updating style properties."""
        session = stage4_service.update_style(
            session_id="test-stage4",
            slide_index=0,
            style_updates={
                "font_size_px": 96,
                "text_color": "#FF0000",
                "alignment": "left",
            },
        )
        assert session is not None
        assert session.slides[0].style.font_size_px == 96
        assert session.slides[0].style.text_color == "#FF0000"
        assert session.slides[0].style.alignment == "left"

    def test_update_style_title_box(self, session_with_images):
        """Test updating title_box style properties."""
        session = stage4_service.update_style(
            session_id="test-stage4",
            slide_index=0,
            style_updates={
                "title_box": {
                    "x_pct": 0.2,
                    "y_pct": 0.4,
                    "w_pct": 0.6,
                },
            },
        )
        assert session.slides[0].style.title_box.x_pct == 0.2
        assert session.slides[0].style.title_box.y_pct == 0.4
        assert session.slides[0].style.title_box.w_pct == 0.6

    def test_update_style_stroke(self, session_with_images):
        """Test updating stroke style properties."""
        session = stage4_service.update_style(
            session_id="test-stage4",
            slide_index=0,
            style_updates={
                "stroke": {
                    "enabled": True,
                    "width_px": 4,
                    "color": "#FF0000",
                },
            },
        )
        assert session.slides[0].style.stroke.enabled is True
        assert session.slides[0].style.stroke.width_px == 4

    def test_apply_style_to_all(self, session_with_images):
        """Test applying style to all slides."""
        session = stage4_service.apply_style_to_all(
            session_id="test-stage4",
            style_updates={"font_size_px": 80},
        )
        assert session is not None
        for slide in session.slides:
            assert slide.style.font_size_px == 80

    def test_suggest_style(self, session_with_images):
        """Test image-based style suggestion."""
        session = asyncio.get_event_loop().run_until_complete(
            stage4_service.suggest_style(
                session_id="test-stage4",
                slide_index=0,
            )
        )
        assert session is not None
        # Should have updated style from image analysis
        assert session.slides[0].style.font_family == "Inter"


class TestStage4Routes:
    """Tests for Stage 4 API routes."""

    def test_apply_all_route(self, client, session_with_images):
        """Test apply all endpoint."""
        response = client.post(
            "/api/stage4/apply-all",
            json={"session_id": "test-stage4"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["session"]["slides"][0]["final_image"] is not None

    def test_apply_single_route(self, client, session_with_images):
        """Test apply single endpoint."""
        response = client.post(
            "/api/stage4/apply",
            json={"session_id": "test-stage4", "slide_index": 0},
        )
        assert response.status_code == 200

    def test_update_style_route(self, client, session_with_images):
        """Test update style endpoint."""
        response = client.post(
            "/api/stage4/update-style",
            json={
                "session_id": "test-stage4",
                "slide_index": 0,
                "style": {"font_size_px": 64, "text_color": "#00FF00"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["session"]["slides"][0]["style"]["font_size_px"] == 64

    def test_apply_style_all_route(self, client, session_with_images):
        """Test apply style to all endpoint."""
        response = client.post(
            "/api/stage4/apply-style-all",
            json={
                "session_id": "test-stage4",
                "style": {"alignment": "right"},
            },
        )
        assert response.status_code == 200

    def test_placeholder_works(self, client):
        """Test that placeholder endpoint still works."""
        response = client.get("/api/stage4/placeholder")
        assert response.status_code == 200
        assert response.json()["stage"] == 4


def font_manager_import():
    """Helper to import font manager."""
    from app.services.font_manager import font_manager
    return font_manager
