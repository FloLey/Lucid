"""Tests for Stage Research — grounded chat and draft extraction."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import container
from tests.conftest import run_async

research_service = container.stage_research
project_manager = container.project_manager


@pytest.fixture
def client():
    """Create a test client."""
    project_manager.clear_all()
    return TestClient(app)


@pytest.fixture
def mock_gemini_chat():
    """Mock generate_chat_response to return a predictable reply."""
    async def _mock_chat(*args, **kwargs):
        return "Here is some useful research about the topic."

    with patch.object(
        container.stage_research.gemini_service,
        "generate_chat_response",
        side_effect=_mock_chat,
    ) as mock:
        yield mock


@pytest.fixture
def mock_gemini_text():
    """Mock generate_text to return a predictable draft."""
    async def _mock_text(*args, **kwargs):
        return "This is the synthesised draft from the research conversation."

    with patch.object(
        container.stage_research.gemini_service,
        "generate_text",
        side_effect=_mock_text,
    ) as mock:
        yield mock


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


class TestStageResearchService:
    """Tests for StageResearchService."""

    def test_send_message_appends_both_turns(self, mock_gemini_chat):
        """send_message adds a user turn and a model turn to chat_history."""
        project_manager.clear_all()
        created = run_async(project_manager.create_project())

        project = run_async(
            research_service.send_message(
                project_id=created.project_id,
                message="Tell me about productivity tips.",
            )
        )

        assert project is not None
        assert len(project.chat_history) == 2
        assert project.chat_history[0]["role"] == "user"
        assert project.chat_history[0]["content"] == "Tell me about productivity tips."
        assert project.chat_history[1]["role"] == "model"
        assert project.chat_history[1]["content"] == "Here is some useful research about the topic."

    def test_send_message_accumulates_history(self, mock_gemini_chat):
        """Repeated send_message calls extend chat_history without overwriting it."""
        project_manager.clear_all()
        created = run_async(project_manager.create_project())

        run_async(research_service.send_message(created.project_id, "First question."))
        project = run_async(research_service.send_message(created.project_id, "Second question."))

        assert len(project.chat_history) == 4  # 2 turns × 2 messages

    def test_send_message_nonexistent_project(self, mock_gemini_chat):
        """send_message returns None for a non-existent project_id."""
        result = run_async(
            research_service.send_message(
                project_id="does-not-exist",
                message="Hello",
            )
        )
        assert result is None

    def test_send_message_rolls_back_user_turn_on_failure(self):
        """If Gemini raises, the user turn is removed and the error is re-raised."""
        project_manager.clear_all()
        created = run_async(project_manager.create_project())

        async def _fail(*args, **kwargs):
            raise RuntimeError("API failure")

        with patch.object(
            container.stage_research.gemini_service,
            "generate_chat_response",
            side_effect=_fail,
        ):
            with pytest.raises(RuntimeError):
                run_async(
                    research_service.send_message(
                        project_id=created.project_id,
                        message="This will fail.",
                    )
                )

        # History must be empty — the failed user turn should have been rolled back
        reloaded = run_async(project_manager.get_project(created.project_id))
        assert reloaded.chat_history == []

    def test_send_message_persists_to_db(self, mock_gemini_chat):
        """chat_history is persisted so it survives a fresh DB read."""
        project_manager.clear_all()
        created = run_async(project_manager.create_project())

        run_async(research_service.send_message(created.project_id, "Persist me."))

        reloaded = run_async(project_manager.get_project(created.project_id))
        assert len(reloaded.chat_history) == 2

    def test_extract_draft_sets_draft_text(self, mock_gemini_text):
        """extract_draft populates project.draft_text with the generated text."""
        project_manager.clear_all()
        created = run_async(project_manager.create_project())
        # Seed some history so there is something to summarise
        created.chat_history = [
            {"role": "user", "content": "Tell me about sleep."},
            {"role": "model", "content": "Sleep is important for health."},
        ]
        run_async(project_manager.update_project(created))

        project = run_async(
            research_service.extract_draft(project_id=created.project_id)
        )

        assert project is not None
        assert project.draft_text == "This is the synthesised draft from the research conversation."

    def test_extract_draft_advances_to_stage_2(self, mock_gemini_text):
        """extract_draft sets current_stage to 2 (Stage Draft) if it was 1."""
        project_manager.clear_all()
        created = run_async(project_manager.create_project())
        assert created.current_stage == 1

        project = run_async(
            research_service.extract_draft(project_id=created.project_id)
        )

        assert project.current_stage == 2

    def test_extract_draft_does_not_lower_stage(self, mock_gemini_text):
        """extract_draft does not reset stage if the project is already past stage 2."""
        project_manager.clear_all()
        created = run_async(project_manager.create_project())
        created.current_stage = 3
        run_async(project_manager.update_project(created))

        project = run_async(
            research_service.extract_draft(project_id=created.project_id)
        )

        assert project.current_stage == 3  # unchanged

    def test_extract_draft_saves_research_instructions(self, mock_gemini_text):
        """research_instructions passed to extract_draft are stored on the project."""
        project_manager.clear_all()
        created = run_async(project_manager.create_project())

        project = run_async(
            research_service.extract_draft(
                project_id=created.project_id,
                research_instructions="Focus on three key arguments",
            )
        )

        assert project.research_instructions == "Focus on three key arguments"

    def test_extract_draft_nonexistent_project(self, mock_gemini_text):
        """extract_draft returns None for a non-existent project_id."""
        result = run_async(
            research_service.extract_draft(project_id="ghost-project")
        )
        assert result is None


# ---------------------------------------------------------------------------
# Route-level tests
# ---------------------------------------------------------------------------


class TestStageResearchRoutes:
    """Tests for /api/stage-research routes."""

    def test_chat_route_returns_updated_project(self, client, mock_gemini_chat):
        """POST /chat returns the project with chat_history populated."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]

        response = client.post(
            "/api/stage-research/chat",
            json={"project_id": project_id, "message": "What are good content ideas?"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "project" in data
        history = data["project"]["chat_history"]
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "model"

    def test_chat_route_empty_message_rejected(self, client):
        """POST /chat with an empty message returns 422."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]

        response = client.post(
            "/api/stage-research/chat",
            json={"project_id": project_id, "message": ""},
        )
        assert response.status_code == 422

    def test_chat_route_nonexistent_project(self, client, mock_gemini_chat):
        """POST /chat with an unknown project_id returns 404."""
        response = client.post(
            "/api/stage-research/chat",
            json={"project_id": "no-such-project", "message": "Hello"},
        )
        assert response.status_code == 404

    def test_extract_draft_route(self, client, mock_gemini_text):
        """POST /extract-draft returns the project with draft_text and stage 2."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]

        response = client.post(
            "/api/stage-research/extract-draft",
            json={
                "project_id": project_id,
                "research_instructions": "Keep it brief",
            },
        )

        assert response.status_code == 200
        data = response.json()
        project = data["project"]
        assert project["draft_text"] != ""
        assert project["current_stage"] == 2
        assert project["research_instructions"] == "Keep it brief"

    def test_extract_draft_route_no_instructions(self, client, mock_gemini_text):
        """POST /extract-draft works without optional research_instructions."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]

        response = client.post(
            "/api/stage-research/extract-draft",
            json={"project_id": project_id},
        )

        assert response.status_code == 200
        assert response.json()["project"]["draft_text"] != ""

    def test_extract_draft_route_nonexistent_project(self, client, mock_gemini_text):
        """POST /extract-draft with an unknown project_id returns 404."""
        response = client.post(
            "/api/stage-research/extract-draft",
            json={"project_id": "ghost"},
        )
        assert response.status_code == 404
