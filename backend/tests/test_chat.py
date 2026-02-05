"""Tests for Chat interface."""

import asyncio
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.services.session_manager import session_manager
from app.services.chat_service import chat_service
from app.models.slide import Slide, SlideText


@pytest.fixture
def client():
    """Create a test client."""
    session_manager.clear_all()
    return TestClient(app)


@pytest.fixture
def session_with_slides():
    """Create a session with slides."""
    session_manager.clear_all()
    session = session_manager.create_session("test-chat")
    session.draft_text = "Test draft content"
    session.slides = [
        Slide(index=0, text=SlideText(title="Slide 1", body="Content 1")),
        Slide(index=1, text=SlideText(title="Slide 2", body="Content 2")),
        Slide(index=2, text=SlideText(title="Slide 3", body="Content 3")),
    ]
    session_manager.update_session(session)
    return session


@pytest.fixture
def mock_gemini():
    """Mock the Gemini service."""
    async def mock_generate_json(prompt, *args, **kwargs):
        # Default routing response
        return {
            "tool": None,
            "response": "Hello! How can I help you today?",
        }

    with patch("app.services.chat_service.gemini_service") as mock:
        mock.generate_json = mock_generate_json
        yield mock


class TestChatService:
    """Tests for ChatService."""

    def test_parse_next_command(self):
        """Test parsing /next command."""
        tool, params = chat_service._parse_explicit_command("/next")
        assert tool == "next_stage"
        assert params == {}

    def test_parse_stage_command(self):
        """Test parsing /stage command."""
        tool, params = chat_service._parse_explicit_command("/stage 3")
        assert tool == "go_to_stage"
        assert params == {"stage": 3}

    def test_parse_regen_slide_command(self):
        """Test parsing /regen slide command."""
        tool, params = chat_service._parse_explicit_command("/regen slide 2")
        assert tool == "regenerate_slide"
        assert params == {"slide_index": 1}  # 0-indexed

    def test_parse_regen_prompt_command(self):
        """Test parsing /regen prompt command."""
        tool, params = chat_service._parse_explicit_command("/regen prompt 3")
        assert tool == "regenerate_prompt"
        assert params == {"slide_index": 2}

    def test_parse_regen_image_command(self):
        """Test parsing /regen image command."""
        tool, params = chat_service._parse_explicit_command("/regen image 1")
        assert tool == "regenerate_image"
        assert params == {"slide_index": 0}

    def test_parse_apply_preset_command(self):
        """Test parsing /apply preset command."""
        tool, params = chat_service._parse_explicit_command("/apply preset bold")
        assert tool == "apply_preset"
        assert params == {"preset": "bold"}

    def test_parse_unknown_command(self):
        """Test parsing unknown command."""
        tool, params = chat_service._parse_explicit_command("Hello there")
        assert tool is None
        assert params == {}

    def test_process_next_command(self, session_with_slides, mock_gemini):
        """Test processing /next command."""
        result = asyncio.get_event_loop().run_until_complete(
            chat_service.process_message("test-chat", "/next")
        )
        assert result["success"] is True
        assert result["tool_called"] == "next_stage"
        assert result["session"]["current_stage"] == 2

    def test_process_stage_command(self, session_with_slides, mock_gemini):
        """Test processing /stage command."""
        result = asyncio.get_event_loop().run_until_complete(
            chat_service.process_message("test-chat", "/stage 3")
        )
        assert result["success"] is True
        assert result["tool_called"] == "go_to_stage"
        assert result["session"]["current_stage"] == 3

    def test_process_no_session(self, mock_gemini):
        """Test processing with no session."""
        session_manager.clear_all()
        result = asyncio.get_event_loop().run_until_complete(
            chat_service.process_message("nonexistent", "/next")
        )
        assert result["success"] is False
        assert "No active session" in result["response"]

    def test_process_greeting(self, session_with_slides, mock_gemini):
        """Test processing a greeting (non-command)."""
        result = asyncio.get_event_loop().run_until_complete(
            chat_service.process_message("test-chat", "Hello!")
        )
        assert result["success"] is True
        assert result["tool_called"] is None


class TestChatRoutes:
    """Tests for Chat API routes."""

    def test_send_message_route(self, client, session_with_slides, mock_gemini):
        """Test the send message endpoint."""
        response = client.post(
            "/api/chat/message",
            json={
                "session_id": "test-chat",
                "message": "/next",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["tool_called"] == "next_stage"

    def test_send_message_validation(self, client):
        """Test message validation."""
        response = client.post(
            "/api/chat/message",
            json={
                "session_id": "test-chat",
                "message": "",  # Empty message
            },
        )
        assert response.status_code == 422

    def test_list_commands_route(self, client):
        """Test the list commands endpoint."""
        response = client.get("/api/chat/commands")
        assert response.status_code == 200
        data = response.json()
        assert "commands" in data
        assert "/next" in data["commands"]
        assert "/stage <1-4>" in data["commands"]

    def test_placeholder_works(self, client):
        """Test that placeholder endpoint still works."""
        response = client.get("/api/chat/placeholder")
        assert response.status_code == 200
        assert response.json()["feature"] == "chat"

    def test_natural_language_routing(self, client, session_with_slides):
        """Test natural language command routing."""
        # Mock a natural language response
        async def mock_nlp(*args, **kwargs):
            return {
                "tool": "go_to_stage",
                "params": {"stage": 2},
                "response": "Moving to Stage 2 for image prompts.",
            }

        with patch("app.services.chat_service.gemini_service") as mock:
            mock.generate_json = mock_nlp
            response = client.post(
                "/api/chat/message",
                json={
                    "session_id": "test-chat",
                    "message": "Let's work on image prompts",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["tool_called"] == "go_to_stage"
