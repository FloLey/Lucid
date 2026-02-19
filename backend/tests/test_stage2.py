"""Tests for Stage 2 - Slide texts to Image prompts."""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import container
from app.models.slide import Slide, SlideText
from tests.conftest import run_async

stage2_service = container.stage2
session_manager = container.session_manager


@pytest.fixture
def client():
    """Create a test client."""
    session_manager.clear_all()
    return TestClient(app)


@pytest.fixture
def session_with_slides():
    """Create a session with slides for testing."""
    session_manager.clear_all()
    session = run_async(session_manager.create_session("test-stage2"))
    session.slides = [
        Slide(index=0, text=SlideText(title="Hook", body="Grab attention")),
        Slide(index=1, text=SlideText(title="Point 1", body="First key point")),
        Slide(index=2, text=SlideText(title="Point 2", body="Second key point")),
    ]
    run_async(session_manager.update_session(session))
    return session


@pytest.fixture
def mock_gemini():
    """Mock the Gemini service for Stage 2."""

    async def mock_generate_json(*args, **kwargs):
        return {"prompt": "Generated image prompt for slide"}

    with patch("app.dependencies.container.stage2.gemini_service") as mock:
        mock.generate_json = mock_generate_json
        yield mock


class TestStage2Service:
    """Tests for Stage2Service."""

    def test_generate_all_prompts(self, session_with_slides, mock_gemini):
        """Test generating prompts for all slides."""
        session = run_async(
            stage2_service.generate_all_prompts(
                session_id="test-stage2",
                image_style_instructions="Warm, inviting colors",
            )
        )
        assert session is not None
        assert session.image_style_instructions == "Warm, inviting colors"
        for slide in session.slides:
            assert slide.image_prompt is not None

    def test_generate_prompts_no_session(self, mock_gemini):
        """Test generating prompts with no session."""
        session_manager.clear_all()
        session = run_async(
            stage2_service.generate_all_prompts(session_id="nonexistent")
        )
        assert session is None

    def test_generate_prompts_no_slides(self, mock_gemini):
        """Test generating prompts with no slides."""
        session_manager.clear_all()
        run_async(session_manager.create_session("empty-session"))
        session = run_async(
            stage2_service.generate_all_prompts(session_id="empty-session")
        )
        assert session is None

    def test_regenerate_prompt(self, session_with_slides, mock_gemini):
        """Test regenerating a single prompt."""
        # First generate all prompts
        run_async(
            stage2_service.generate_all_prompts(session_id="test-stage2")
        )

        # Mock for single regeneration
        async def mock_single(*args, **kwargs):
            return {"prompt": "New regenerated prompt"}

        mock_gemini.generate_json = mock_single

        session = run_async(
            stage2_service.regenerate_prompt(
                session_id="test-stage2",
                slide_index=1,
            )
        )
        assert session is not None
        assert session.slides[1].image_prompt == "New regenerated prompt"

    def test_regenerate_prompt_invalid_index(self, session_with_slides, mock_gemini):
        """Test regenerating prompt with invalid index."""
        session = run_async(
            stage2_service.regenerate_prompt(
                session_id="test-stage2",
                slide_index=99,
            )
        )
        assert session is None

    def test_update_prompt(self, session_with_slides):
        """Test manually updating a prompt."""
        session = run_async(
            stage2_service.update_prompt(
                session_id="test-stage2",
                slide_index=0,
                prompt="Custom image prompt",
            )
        )
        assert session is not None
        assert session.slides[0].image_prompt == "Custom image prompt"

    def test_update_prompt_invalid_index(self, session_with_slides):
        """Test updating prompt with invalid index."""
        session = run_async(
            stage2_service.update_prompt(
                session_id="test-stage2",
                slide_index=99,
                prompt="Custom prompt",
            )
        )
        assert session is None

    def test_update_style_instructions(self, session_with_slides):
        """Test updating style instructions."""
        session = run_async(
            stage2_service.update_style_instructions(
                session_id="test-stage2",
                style_instructions="Vintage, retro aesthetic",
            )
        )
        assert session is not None
        assert session.image_style_instructions == "Vintage, retro aesthetic"

    def test_update_style_no_session(self):
        """Test updating style with no session."""
        session_manager.clear_all()
        session = run_async(
            stage2_service.update_style_instructions(
                session_id="nonexistent",
                style_instructions="Test",
            )
        )
        assert session is None


class TestStage2Routes:
    """Tests for Stage 2 API routes."""

    def test_generate_prompts_route(self, client, mock_gemini):
        """Test the generate prompts endpoint."""
        # Create session with slides first
        run_async(session_manager.create_session("route-test-001"))
        session = run_async(session_manager.get_session("route-test-001"))
        session.slides = [
            Slide(index=0, text=SlideText(body="Test content 1")),
            Slide(index=1, text=SlideText(body="Test content 2")),
        ]
        run_async(session_manager.update_session(session))

        response = client.post(
            "/api/stage2/generate",
            json={
                "session_id": "route-test-001",
                "image_style_instructions": "Modern, clean style",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "session" in data
        assert data["session"]["slides"][0]["image_prompt"] is not None

    def test_generate_prompts_no_session(self, client):
        """Test generate prompts with no session."""
        response = client.post(
            "/api/stage2/generate",
            json={"session_id": "nonexistent"},
        )
        assert response.status_code == 404

    def test_regenerate_prompt_route(self, client, mock_gemini):
        """Test the regenerate prompt endpoint."""
        # Create session with slides and prompts
        run_async(session_manager.create_session("route-test-002"))
        session = run_async(session_manager.get_session("route-test-002"))
        session.slides = [
            Slide(index=0, text=SlideText(body="Content"), image_prompt="Original"),
            Slide(index=1, text=SlideText(body="Content 2"), image_prompt="Original 2"),
        ]
        run_async(session_manager.update_session(session))

        response = client.post(
            "/api/stage2/regenerate",
            json={"session_id": "route-test-002", "slide_index": 0},
        )
        assert response.status_code == 200

    def test_update_prompt_route(self, client):
        """Test the update prompt endpoint."""
        # Create session with slides
        run_async(session_manager.create_session("route-test-003"))
        session = run_async(session_manager.get_session("route-test-003"))
        session.slides = [Slide(index=0, text=SlideText(body="Content"))]
        run_async(session_manager.update_session(session))

        response = client.post(
            "/api/stage2/update",
            json={
                "session_id": "route-test-003",
                "slide_index": 0,
                "prompt": "Custom image: sunset over mountains",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert (
            data["session"]["slides"][0]["image_prompt"]
            == "Custom image: sunset over mountains"
        )

    def test_update_style_route(self, client):
        """Test the update style endpoint."""
        run_async(session_manager.create_session("route-test-004"))

        response = client.post(
            "/api/stage2/style",
            json={
                "session_id": "route-test-004",
                "style_instructions": "Vibrant, energetic colors",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert (
            data["session"]["image_style_instructions"] == "Vibrant, energetic colors"
        )

    def test_placeholder_works(self, client):
        """Test that placeholder endpoint still works."""
        response = client.get("/api/stage2/placeholder")
        assert response.status_code == 200
        assert response.json()["stage"] == 2
