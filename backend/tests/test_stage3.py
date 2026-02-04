"""Tests for Stage 3 - Image prompts to Images."""

import asyncio
import base64
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.services.session_manager import session_manager
from app.services.stage3_service import stage3_service
from app.services.image_service import image_service
from app.models.slide import Slide, SlideText


@pytest.fixture
def client():
    """Create a test client."""
    session_manager.clear_all()
    return TestClient(app)


@pytest.fixture
def session_with_prompts():
    """Create a session with image prompts."""
    session_manager.clear_all()
    session = session_manager.create_session("test-stage3")
    session.shared_prompt_prefix = "Modern minimalist style"
    session.slides = [
        Slide(
            index=0,
            text=SlideText(title="Hook", body="Grab attention"),
            image_prompt="Warm sunset gradient background",
        ),
        Slide(
            index=1,
            text=SlideText(title="Point 1", body="First key point"),
            image_prompt="Cool blue abstract shapes",
        ),
        Slide(
            index=2,
            text=SlideText(title="Point 2", body="Second key point"),
            image_prompt="Green nature-inspired pattern",
        ),
    ]
    session_manager.update_session(session)
    return session


@pytest.fixture
def mock_image_service():
    """Mock the image service."""
    # Create a simple 10x10 PNG as mock data
    async def mock_generate(*args, **kwargs):
        return "iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mNk+M9Qz0AEYBxVSF+FABJADq3/"

    with patch.object(image_service, "generate_image", mock_generate):
        yield


class TestImageService:
    """Tests for ImageService."""

    def test_generate_placeholder(self):
        """Test placeholder image generation."""
        base64_data = image_service._generate_placeholder("Test prompt")
        assert base64_data is not None
        # Should be valid base64
        decoded = base64.b64decode(base64_data)
        # Should be PNG (starts with PNG signature)
        assert decoded[:8] == b"\x89PNG\r\n\x1a\n"

    def test_generate_different_placeholders(self):
        """Test that different prompts generate different placeholders."""
        img1 = image_service._generate_placeholder("Prompt A")
        img2 = image_service._generate_placeholder("Prompt B")
        # Different prompts should create different images
        assert img1 != img2

    def test_decode_encode_roundtrip(self):
        """Test decoding and re-encoding an image."""
        original = image_service._generate_placeholder("Test")
        decoded = image_service.decode_image(original)
        re_encoded = image_service.encode_image(decoded)
        # Re-decoding should work
        image_service.decode_image(re_encoded)


class TestStage3Service:
    """Tests for Stage3Service."""

    def test_generate_all_images(self, session_with_prompts, mock_image_service):
        """Test generating images for all slides."""
        session = asyncio.get_event_loop().run_until_complete(
            stage3_service.generate_all_images(session_id="test-stage3")
        )
        assert session is not None
        for slide in session.slides:
            assert slide.image_data is not None
            # Should be valid base64
            base64.b64decode(slide.image_data)

    def test_generate_images_no_session(self, mock_image_service):
        """Test generating images with no session."""
        session_manager.clear_all()
        session = asyncio.get_event_loop().run_until_complete(
            stage3_service.generate_all_images(session_id="nonexistent")
        )
        assert session is None

    def test_generate_images_fills_missing_prompts(self, mock_image_service):
        """Test that missing prompts are filled with defaults."""
        session_manager.clear_all()
        session = session_manager.create_session("test-fill")
        session.slides = [
            Slide(index=0, text=SlideText(body="Content")),  # No prompt
        ]
        session_manager.update_session(session)

        result = asyncio.get_event_loop().run_until_complete(
            stage3_service.generate_all_images(session_id="test-fill")
        )
        assert result.slides[0].image_prompt is not None
        assert result.slides[0].image_data is not None

    def test_regenerate_image(self, session_with_prompts, mock_image_service):
        """Test regenerating a single image."""
        # First generate all
        asyncio.get_event_loop().run_until_complete(
            stage3_service.generate_all_images(session_id="test-stage3")
        )

        original_data = session_manager.get_session("test-stage3").slides[1].image_data

        # Regenerate slide 1
        session = asyncio.get_event_loop().run_until_complete(
            stage3_service.regenerate_image(
                session_id="test-stage3",
                slide_index=1,
            )
        )
        assert session is not None
        # Image should be regenerated (we can't guarantee it's different with mocks)
        assert session.slides[1].image_data is not None

    def test_regenerate_image_invalid_index(self, session_with_prompts, mock_image_service):
        """Test regenerating image with invalid index."""
        session = asyncio.get_event_loop().run_until_complete(
            stage3_service.regenerate_image(
                session_id="test-stage3",
                slide_index=99,
            )
        )
        assert session is None

    def test_set_image_data(self, session_with_prompts):
        """Test setting image data directly."""
        custom_data = "custombase64imagedata"
        session = stage3_service.set_image_data(
            session_id="test-stage3",
            slide_index=0,
            image_data=custom_data,
        )
        assert session is not None
        assert session.slides[0].image_data == custom_data

    def test_set_image_data_invalid_index(self, session_with_prompts):
        """Test setting image data with invalid index."""
        session = stage3_service.set_image_data(
            session_id="test-stage3",
            slide_index=99,
            image_data="test",
        )
        assert session is None


class TestStage3Routes:
    """Tests for Stage 3 API routes."""

    def test_generate_images_route(self, client, mock_image_service):
        """Test the generate images endpoint."""
        # Create session with slides and prompts
        session_manager.create_session("route-test-001")
        session = session_manager.get_session("route-test-001")
        session.slides = [
            Slide(index=0, text=SlideText(body="Content"), image_prompt="Test prompt"),
            Slide(index=1, text=SlideText(body="Content 2"), image_prompt="Test prompt 2"),
        ]
        session_manager.update_session(session)

        response = client.post(
            "/api/stage3/generate",
            json={"session_id": "route-test-001"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "session" in data
        assert data["session"]["slides"][0]["image_data"] is not None

    def test_generate_images_no_session(self, client):
        """Test generate images with no session."""
        response = client.post(
            "/api/stage3/generate",
            json={"session_id": "nonexistent"},
        )
        assert response.status_code == 404

    def test_regenerate_image_route(self, client, mock_image_service):
        """Test the regenerate image endpoint."""
        # Create session with slides and images
        session_manager.create_session("route-test-002")
        session = session_manager.get_session("route-test-002")
        session.slides = [
            Slide(index=0, text=SlideText(body="Content"), image_prompt="Prompt", image_data="existing"),
        ]
        session_manager.update_session(session)

        response = client.post(
            "/api/stage3/regenerate",
            json={"session_id": "route-test-002", "slide_index": 0},
        )
        assert response.status_code == 200

    def test_upload_image_route(self, client):
        """Test the upload/set image endpoint."""
        session_manager.create_session("route-test-003")
        session = session_manager.get_session("route-test-003")
        session.slides = [Slide(index=0, text=SlideText(body="Content"))]
        session_manager.update_session(session)

        response = client.post(
            "/api/stage3/upload",
            json={
                "session_id": "route-test-003",
                "slide_index": 0,
                "image_data": "custombase64data",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["session"]["slides"][0]["image_data"] == "custombase64data"

    def test_placeholder_works(self, client):
        """Test that placeholder endpoint still works."""
        response = client.get("/api/stage3/placeholder")
        assert response.status_code == 200
        assert response.json()["stage"] == 3
