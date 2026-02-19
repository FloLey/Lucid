"""Tests for Stage Style - Visual style proposal generation and selection."""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import container
from app.models.slide import Slide, SlideText
from tests.conftest import run_async

session_manager = container.session_manager
stage_style_service = container.stage_style


@pytest.fixture
def client():
    """Create a test client."""
    session_manager.clear_all()
    return TestClient(app)


@pytest.fixture
def session_with_slides():
    """Create a session with slides."""
    session_manager.clear_all()
    session = run_async(session_manager.create_session("test-style"))
    session.draft_text = "Test draft content"
    session.slides = [
        Slide(index=0, text=SlideText(title="Slide 1", body="Content 1")),
        Slide(index=1, text=SlideText(title="Slide 2", body="Content 2")),
        Slide(index=2, text=SlideText(title="Slide 3", body="Content 3")),
    ]
    run_async(session_manager.update_session(session))
    return session


@pytest.fixture
def mock_gemini_and_image():
    """Mock both Gemini and image services."""

    async def mock_generate_json(prompt, *args, **kwargs):
        return {
            "proposals": [
                {
                    "description": "Warm sunset tones with golden gradients",
                    "image_prompt": "Warm sunset gradient background",
                },
                {
                    "description": "Cool blue minimalist aesthetic",
                    "image_prompt": "Cool blue minimalist background",
                },
                {
                    "description": "Dark moody professional style",
                    "image_prompt": "Dark moody professional background",
                },
            ]
        }

    async def mock_generate_image(prompt, *args, **kwargs):
        return "fakebase64imagedata"

    with (
        patch.object(stage_style_service, "gemini_service") as mock_gemini,
        patch.object(stage_style_service, "image_service") as mock_image,
    ):
        mock_gemini.generate_json = mock_generate_json
        mock_image.generate_image = mock_generate_image
        yield mock_gemini, mock_image


class TestStageStyleService:
    """Tests for StageStyleService."""

    def test_generate_proposals(self, session_with_slides, mock_gemini_and_image):
        """Test generating style proposals."""
        session = run_async(
            stage_style_service.generate_proposals("test-style", num_proposals=3)
        )
        assert session is not None
        assert len(session.style_proposals) == 3
        assert (
            session.style_proposals[0].description
            == "Warm sunset tones with golden gradients"
        )
        assert session.style_proposals[0].preview_image == "fakebase64imagedata"
        assert session.selected_style_proposal_index is None

    def test_generate_proposals_no_session(self, mock_gemini_and_image):
        """Test generating proposals with no session."""
        session_manager.clear_all()
        session = run_async(
            stage_style_service.generate_proposals("nonexistent")
        )
        assert session is None

    def test_select_proposal(self, session_with_slides, mock_gemini_and_image):
        """Test selecting a style proposal."""
        # First generate proposals
        run_async(
            stage_style_service.generate_proposals("test-style")
        )
        # Then select one
        session = run_async(
            stage_style_service.select_proposal("test-style", 1)
        )
        assert session is not None
        assert session.selected_style_proposal_index == 1
        assert session.shared_prompt_prefix == "Cool blue minimalist aesthetic"

    def test_select_invalid_proposal(self, session_with_slides, mock_gemini_and_image):
        """Test selecting an invalid proposal index."""
        run_async(
            stage_style_service.generate_proposals("test-style")
        )
        session = run_async(
            stage_style_service.select_proposal("test-style", 10)
        )
        assert session is None

    def test_select_proposal_no_session(self):
        """Test selecting proposal with no session."""
        session_manager.clear_all()
        session = run_async(
            stage_style_service.select_proposal("nonexistent", 0)
        )
        assert session is None


class TestStageStyleRoutes:
    """Tests for Stage Style API routes."""

    def test_generate_route(self, client, session_with_slides, mock_gemini_and_image):
        """Test the generate proposals endpoint."""
        response = client.post(
            "/api/stage-style/generate",
            json={"session_id": "test-style", "num_proposals": 3},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["session"]["style_proposals"]) == 3

    def test_select_route(self, client, session_with_slides, mock_gemini_and_image):
        """Test the select proposal endpoint."""
        # Generate first
        client.post(
            "/api/stage-style/generate",
            json={"session_id": "test-style", "num_proposals": 3},
        )
        # Select
        response = client.post(
            "/api/stage-style/select",
            json={"session_id": "test-style", "proposal_index": 0},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["session"]["selected_style_proposal_index"] == 0

    def test_generate_no_session(self, client):
        """Test generating proposals with no session."""
        response = client.post(
            "/api/stage-style/generate",
            json={"session_id": "nonexistent"},
        )
        assert response.status_code == 404

    def test_placeholder_works(self, client):
        """Test that placeholder endpoint still works."""
        response = client.get("/api/stage-style/placeholder")
        assert response.status_code == 200
        assert response.json()["stage"] == "style"
