"""Tests for Stage 1 - Draft to Slide texts."""

import asyncio
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.services.session_manager import session_manager
from app.services.stage1_service import stage1_service
from app.models.slide import Slide, SlideText


@pytest.fixture
def client():
    """Create a test client."""
    session_manager.clear_all()
    return TestClient(app)


@pytest.fixture
def mock_gemini():
    """Mock the Gemini service to return predictable results."""
    import json
    mock_response = json.dumps({
        "slides": [
            {"title": "Slide 1", "body": "Content 1"},
            {"title": "Slide 2", "body": "Content 2"},
            {"title": "Slide 3", "body": "Content 3"},
            {"title": "Slide 4", "body": "Content 4"},
            {"title": "Slide 5", "body": "Content 5"},
        ]
    })

    async def mock_generate_json(*args, **kwargs):
        return {
            "slides": [
                {"title": "Slide 1", "body": "Content 1"},
                {"title": "Slide 2", "body": "Content 2"},
                {"title": "Slide 3", "body": "Content 3"},
                {"title": "Slide 4", "body": "Content 4"},
                {"title": "Slide 5", "body": "Content 5"},
            ]
        }

    with patch("app.services.stage1_service.gemini_service") as mock:
        mock.generate_json = mock_generate_json
        yield mock


class TestStage1Service:
    """Tests for Stage1Service."""

    def test_generate_slide_texts_creates_session(self, mock_gemini):
        """Test that generate_slide_texts creates a session."""
        session_manager.clear_all()
        session = asyncio.get_event_loop().run_until_complete(
            stage1_service.generate_slide_texts(
                session_id="test-stage1-001",
                draft_text="This is a test draft about productivity tips.",
                num_slides=3,
                include_titles=True,
            )
        )
        assert session is not None
        assert session.session_id == "test-stage1-001"
        assert len(session.slides) == 3

    def test_generate_slide_texts_stores_inputs(self, mock_gemini):
        """Test that inputs are stored in session."""
        session_manager.clear_all()
        session = asyncio.get_event_loop().run_until_complete(
            stage1_service.generate_slide_texts(
                session_id="test-stage1-002",
                draft_text="Test draft content",
                num_slides=5,
                include_titles=False,
                additional_instructions="Make it funny",
            )
        )
        assert session.draft_text == "Test draft content"
        assert session.num_slides == 5
        assert session.include_titles is False
        assert session.additional_instructions == "Make it funny"

    def test_generate_slide_texts_with_titles(self, mock_gemini):
        """Test slide generation with titles."""
        session_manager.clear_all()
        session = asyncio.get_event_loop().run_until_complete(
            stage1_service.generate_slide_texts(
                session_id="test-stage1-003",
                draft_text="Test content for slides",
                num_slides=3,
                include_titles=True,
            )
        )
        # All slides should have content
        for slide in session.slides:
            assert slide.text.title is not None or slide.text.body != ""

    def test_regenerate_all_requires_draft(self, mock_gemini):
        """Test that regenerate_all requires existing draft."""
        session_manager.clear_all()
        session_manager.create_session("test-stage1-004")
        result = asyncio.get_event_loop().run_until_complete(
            stage1_service.regenerate_all_slide_texts("test-stage1-004")
        )
        assert result is None  # No draft stored

    def test_regenerate_single_slide(self, mock_gemini):
        """Test regenerating a single slide."""
        session_manager.clear_all()
        asyncio.get_event_loop().run_until_complete(
            stage1_service.generate_slide_texts(
                session_id="test-stage1-005",
                draft_text="Test content",
                num_slides=3,
            )
        )

        session = asyncio.get_event_loop().run_until_complete(
            stage1_service.regenerate_slide_text(
                session_id="test-stage1-005",
                slide_index=1,
            )
        )
        assert session is not None
        assert len(session.slides) == 3

    def test_update_slide_text(self):
        """Test manually updating slide text."""
        session_manager.clear_all()
        session = session_manager.create_session("test-stage1-006")
        session.slides = [Slide(index=0)]
        session_manager.update_session(session)

        result = stage1_service.update_slide_text(
            session_id="test-stage1-006",
            slide_index=0,
            title="New Title",
            body="New Body",
        )
        assert result is not None
        assert result.slides[0].text.title == "New Title"
        assert result.slides[0].text.body == "New Body"

    def test_update_slide_text_partial(self):
        """Test partially updating slide text."""
        session_manager.clear_all()
        session = session_manager.create_session("test-stage1-007")
        session.slides = [
            Slide(index=0, text=SlideText(title="Original", body="Original body"))
        ]
        session_manager.update_session(session)

        result = stage1_service.update_slide_text(
            session_id="test-stage1-007",
            slide_index=0,
            body="Updated body only",
        )
        assert result.slides[0].text.title == "Original"  # Unchanged
        assert result.slides[0].text.body == "Updated body only"

    def test_update_nonexistent_slide(self):
        """Test updating a nonexistent slide."""
        session_manager.clear_all()
        session_manager.create_session("test-stage1-008")
        result = stage1_service.update_slide_text(
            session_id="test-stage1-008",
            slide_index=99,
            body="New content",
        )
        assert result is None


class TestStage1Routes:
    """Tests for Stage 1 API routes."""

    def test_generate_slide_texts_route(self, client, mock_gemini):
        """Test the generate slide texts endpoint."""
        response = client.post(
            "/api/stage1/generate",
            json={
                "session_id": "route-test-001",
                "draft_text": "This is my draft about social media tips.",
                "num_slides": 4,
                "include_titles": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "session" in data
        assert data["session"]["session_id"] == "route-test-001"
        assert len(data["session"]["slides"]) == 4

    def test_generate_slide_texts_validation(self, client):
        """Test input validation for generate endpoint."""
        response = client.post(
            "/api/stage1/generate",
            json={
                "session_id": "route-test-002",
                "draft_text": "",
                "num_slides": 5,
            },
        )
        assert response.status_code == 422  # Validation error

    def test_generate_slide_texts_num_slides_bounds(self, client):
        """Test num_slides bounds validation."""
        response = client.post(
            "/api/stage1/generate",
            json={
                "session_id": "route-test-003",
                "draft_text": "Test draft",
                "num_slides": 25,  # Max is 20
            },
        )
        assert response.status_code == 422

    def test_regenerate_all_route(self, client, mock_gemini):
        """Test regenerate all endpoint."""
        client.post(
            "/api/stage1/generate",
            json={
                "session_id": "route-test-004",
                "draft_text": "Original draft content",
                "num_slides": 3,
            },
        )
        response = client.post(
            "/api/stage1/regenerate-all",
            json={"session_id": "route-test-004"},
        )
        assert response.status_code == 200
        assert len(response.json()["session"]["slides"]) == 3

    def test_regenerate_all_no_draft(self, client):
        """Test regenerate all without prior generation."""
        client.post("/api/sessions/create", json={"session_id": "route-test-005"})
        response = client.post(
            "/api/stage1/regenerate-all",
            json={"session_id": "route-test-005"},
        )
        assert response.status_code == 404

    def test_regenerate_single_route(self, client, mock_gemini):
        """Test regenerate single slide endpoint."""
        client.post(
            "/api/stage1/generate",
            json={
                "session_id": "route-test-006",
                "draft_text": "Test content for slides",
                "num_slides": 3,
            },
        )
        response = client.post(
            "/api/stage1/regenerate",
            json={"session_id": "route-test-006", "slide_index": 1},
        )
        assert response.status_code == 200

    def test_update_slide_route(self, client, mock_gemini):
        """Test update slide text endpoint."""
        client.post(
            "/api/stage1/generate",
            json={
                "session_id": "route-test-007",
                "draft_text": "Test content",
                "num_slides": 2,
            },
        )
        response = client.post(
            "/api/stage1/update",
            json={
                "session_id": "route-test-007",
                "slide_index": 0,
                "title": "Custom Title",
                "body": "Custom body content",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["session"]["slides"][0]["text"]["title"] == "Custom Title"
        assert data["session"]["slides"][0]["text"]["body"] == "Custom body content"

    def test_placeholder_still_works(self, client):
        """Test that placeholder endpoint still works."""
        response = client.get("/api/stage1/placeholder")
        assert response.status_code == 200
        assert response.json()["stage"] == 1
