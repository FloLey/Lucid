"""Tests for Chat interface."""

import asyncio
import json
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.services.session_manager import session_manager
from app.services.chat_service import chat_service, cancel_agent, _cancel_flags, READ_TOOLS, _get_tool_declarations
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


def _parse_sse_events(response_text: str) -> list:
    """Parse SSE events from response text."""
    events = []
    for line in response_text.strip().split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            data = json.loads(line[6:])
            events.append(data)
    return events


class TestChatService:
    """Tests for ChatService."""

    def test_parse_next_command(self):
        """Test parsing /next command."""
        tool, params = chat_service._parse_explicit_command("/next")
        assert tool == "next_stage"
        assert params == {}

    def test_parse_back_command(self):
        """Test parsing /back command."""
        tool, params = chat_service._parse_explicit_command("/back")
        assert tool == "back_stage"
        assert params == {}

    def test_parse_stage_command(self):
        """Test parsing /stage command."""
        tool, params = chat_service._parse_explicit_command("/stage 3")
        assert tool == "go_to_stage"
        assert params == {"stage": 3}

    def test_parse_regen_slide_command(self):
        """Test parsing /regen slide command (1-based index)."""
        tool, params = chat_service._parse_explicit_command("/regen slide 2")
        assert tool == "regenerate_slide"
        assert params == {"slide_index": 2}  # 1-based

    def test_parse_regen_prompt_command(self):
        """Test parsing /regen prompt command (1-based index)."""
        tool, params = chat_service._parse_explicit_command("/regen prompt 3")
        assert tool == "regenerate_prompt"
        assert params == {"slide_index": 3}  # 1-based

    def test_parse_regen_image_command(self):
        """Test parsing /regen image command (1-based index)."""
        tool, params = chat_service._parse_explicit_command("/regen image 1")
        assert tool == "regenerate_image"
        assert params == {"slide_index": 1}  # 1-based

    def test_parse_generate_command(self):
        """Test parsing /generate command."""
        tool, params = chat_service._parse_explicit_command("/generate")
        assert tool == "auto_generate"
        assert params == {}

    def test_parse_export_command(self):
        """Test parsing /export command."""
        tool, params = chat_service._parse_explicit_command("/export")
        assert tool == "export"
        assert params == {}

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


class TestReadTools:
    """Tests for read tool implementations."""

    def test_get_slide(self, session_with_slides):
        """Test get_slide read tool."""
        result = chat_service._execute_read_tool("test-chat", "get_slide", {"slide_index": 2})
        assert result["index"] == 2
        assert result["title"] == "Slide 2"
        assert result["body"] == "Content 2"

    def test_get_slide_out_of_range(self, session_with_slides):
        """Test get_slide with invalid index."""
        result = chat_service._execute_read_tool("test-chat", "get_slide", {"slide_index": 10})
        assert "error" in result

    def test_get_all_slides(self, session_with_slides):
        """Test get_all_slides read tool."""
        result = chat_service._execute_read_tool("test-chat", "get_all_slides", {})
        assert len(result["slides"]) == 3
        assert result["slides"][0]["index"] == 1
        assert result["slides"][0]["title"] == "Slide 1"

    def test_get_draft(self, session_with_slides):
        """Test get_draft read tool."""
        result = chat_service._execute_read_tool("test-chat", "get_draft", {})
        assert result["draft_text"] == "Test draft content"

    def test_get_session_info(self, session_with_slides):
        """Test get_session_info read tool."""
        result = chat_service._execute_read_tool("test-chat", "get_session_info", {})
        assert result["current_stage"] == 1
        assert result["num_slides"] == 3
        assert result["language"] == "English"

    def test_get_style_proposals_empty(self, session_with_slides):
        """Test get_style_proposals when none exist."""
        result = chat_service._execute_read_tool("test-chat", "get_style_proposals", {})
        assert result["proposals"] == []
        assert result["selected_index"] is None

    def test_no_session(self):
        """Test read tool with no session."""
        session_manager.clear_all()
        result = chat_service._execute_read_tool("nonexistent", "get_slide", {"slide_index": 1})
        assert "error" in result


class TestToolDeclarations:
    """Tests for tool declaration generation."""

    def test_stage1_has_write_tools(self):
        """Test that stage 1 includes slide write tools."""
        declarations = _get_tool_declarations(1)
        names = {d["name"] for d in declarations}
        assert "generate_slides" in names
        assert "regenerate_slide" in names
        assert "update_slide" in names
        # Should not have other stage tools
        assert "generate_images" not in names
        assert "apply_styles" not in names

    def test_stage4_has_image_tools(self):
        """Test that stage 4 includes image tools."""
        declarations = _get_tool_declarations(4)
        names = {d["name"] for d in declarations}
        assert "generate_images" in names
        assert "regenerate_image" in names
        # Should not have stage 1 write tools
        assert "generate_slides" not in names

    def test_all_stages_have_read_tools(self):
        """Test that all stages include read tools."""
        for stage in range(1, 6):
            declarations = _get_tool_declarations(stage)
            names = {d["name"] for d in declarations}
            for read_tool in READ_TOOLS:
                assert read_tool in names, f"Stage {stage} missing {read_tool}"

    def test_all_stages_have_nav_tools(self):
        """Test that all stages include navigation tools."""
        for stage in range(1, 6):
            declarations = _get_tool_declarations(stage)
            names = {d["name"] for d in declarations}
            assert "next_stage" in names
            assert "back_stage" in names
            assert "go_to_stage" in names


class TestSessionSnapshots:
    """Tests for session snapshot/undo functionality."""

    def test_take_and_restore_snapshot(self, session_with_slides):
        """Test taking and restoring a snapshot."""
        # Take snapshot
        session_manager.take_snapshot("test-chat")

        # Modify session
        session = session_manager.get_session("test-chat")
        session.slides[0].text.body = "Modified content"
        session_manager.update_session(session)

        # Verify modification
        session = session_manager.get_session("test-chat")
        assert session.slides[0].text.body == "Modified content"

        # Restore snapshot
        restored = session_manager.restore_snapshot("test-chat")
        assert restored is not None
        assert restored.slides[0].text.body == "Content 1"

        # Snapshot should be cleared
        assert session_manager.get_snapshot("test-chat") is None

    def test_restore_no_snapshot(self):
        """Test restoring when no snapshot exists."""
        session_manager.clear_all()
        result = session_manager.restore_snapshot("nonexistent")
        assert result is None

    def test_snapshot_is_deep_copy(self, session_with_slides):
        """Test that snapshot is a deep copy (mutations don't affect it)."""
        session_manager.take_snapshot("test-chat")

        # Mutate the original session
        session = session_manager.get_session("test-chat")
        session.slides.clear()
        session_manager.update_session(session)

        # Snapshot should still have slides
        snapshot = session_manager.get_snapshot("test-chat")
        assert len(snapshot.slides) == 3


class TestCancelAgent:
    """Tests for agent cancellation."""

    def test_cancel_sets_flag(self):
        """Test that cancel_agent sets the flag."""
        cancel_agent("test-session")
        assert _cancel_flags.get("test-session") is True
        # Clean up
        _cancel_flags.pop("test-session", None)


class TestChatRoutes:
    """Tests for Chat API routes."""

    def test_send_message_sse(self, client, session_with_slides):
        """Test the send message endpoint returns SSE for /next."""
        response = client.post(
            "/api/chat/message",
            json={
                "session_id": "test-chat",
                "message": "/next",
            },
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        events = _parse_sse_events(response.text)
        # Should have tool_call, tool_result, and done events
        event_types = [e["event"] for e in events]
        assert "tool_call" in event_types
        assert "tool_result" in event_types
        assert "done" in event_types

        # Done event should have updated session
        done_event = next(e for e in events if e["event"] == "done")
        assert done_event["session"]["current_stage"] == 2

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

    def test_cancel_endpoint(self, client):
        """Test the cancel endpoint."""
        response = client.post(
            "/api/chat/cancel",
            json={"session_id": "test-chat"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_undo_no_snapshot(self, client):
        """Test undo when no snapshot exists."""
        session_manager.clear_all()
        session_manager.create_session("test-chat")
        response = client.post(
            "/api/chat/undo",
            json={"session_id": "test-chat"},
        )
        assert response.status_code == 404

    def test_undo_with_snapshot(self, client, session_with_slides):
        """Test undo restores snapshot."""
        # Take a snapshot
        session_manager.take_snapshot("test-chat")

        # Modify session
        session = session_manager.get_session("test-chat")
        session.slides[0].text.body = "Modified"
        session_manager.update_session(session)

        # Undo
        response = client.post(
            "/api/chat/undo",
            json={"session_id": "test-chat"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["session"]["slides"][0]["text"]["body"] == "Content 1"

    def test_list_commands_route(self, client):
        """Test the list commands endpoint."""
        response = client.get("/api/chat/commands")
        assert response.status_code == 200
        data = response.json()
        assert "commands" in data
        assert "/next" in data["commands"]
        assert "/back" in data["commands"]
        assert "/stage <1-5>" in data["commands"]

    def test_placeholder_works(self, client):
        """Test that placeholder endpoint still works."""
        response = client.get("/api/chat/placeholder")
        assert response.status_code == 200
        assert response.json()["feature"] == "chat"
