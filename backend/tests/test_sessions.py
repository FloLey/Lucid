"""Tests for session management."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import container
from tests.conftest import run_async

session_manager = container.session_manager


@pytest.fixture
def client():
    """Create a test client."""
    session_manager.clear_all()
    return TestClient(app)


class TestSessionManager:
    """Tests for SessionManager service."""

    def test_create_session(self):
        """Test creating a new session."""
        session_manager.clear_all()
        session = run_async(session_manager.create_session("test-001"))
        assert session.session_id == "test-001"
        assert session.current_stage == 1

    def test_create_existing_session(self):
        """Test creating a session that already exists."""
        session_manager.clear_all()
        session1 = run_async(session_manager.create_session("test-002"))
        session2 = run_async(session_manager.create_session("test-002"))
        assert session1 is session2

    def test_get_session(self):
        """Test getting a session."""
        session_manager.clear_all()
        run_async(session_manager.create_session("test-003"))
        session = run_async(session_manager.get_session("test-003"))
        assert session is not None
        assert session.session_id == "test-003"

    def test_get_nonexistent_session(self):
        """Test getting a session that doesn't exist."""
        session_manager.clear_all()
        session = run_async(session_manager.get_session("nonexistent"))
        assert session is None

    def test_delete_session(self):
        """Test deleting a session."""
        session_manager.clear_all()
        run_async(session_manager.create_session("test-004"))
        assert run_async(session_manager.delete_session("test-004")) is True
        assert run_async(session_manager.get_session("test-004")) is None

    def test_delete_nonexistent_session(self):
        """Test deleting a nonexistent session."""
        session_manager.clear_all()
        assert run_async(session_manager.delete_session("nonexistent")) is False

    def test_advance_stage(self):
        """Test advancing to next stage."""
        session_manager.clear_all()
        run_async(session_manager.create_session("test-005"))
        session = run_async(session_manager.advance_stage("test-005"))
        assert session.current_stage == 2
        session = run_async(session_manager.advance_stage("test-005"))
        assert session.current_stage == 3

    def test_advance_stage_max(self):
        """Test advancing past max stage."""
        session_manager.clear_all()
        session = run_async(session_manager.create_session("test-006"))
        session.current_stage = 5
        session = run_async(session_manager.advance_stage("test-006"))
        assert session.current_stage == 5  # Should not go past 5

    def test_go_to_stage(self):
        """Test going to a specific stage."""
        session_manager.clear_all()
        run_async(session_manager.create_session("test-007"))
        session = run_async(session_manager.go_to_stage("test-007", 3))
        assert session.current_stage == 3


class TestSessionRoutes:
    """Tests for session API routes."""

    def test_list_sessions_empty(self, client):
        """Test listing sessions when empty."""
        response = client.get("/api/sessions/")
        assert response.status_code == 200
        assert response.json()["sessions"] == []

    def test_create_session_route(self, client):
        """Test creating a session via API."""
        response = client.post(
            "/api/sessions/create",
            json={"session_id": "api-test-001"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["session"]["session_id"] == "api-test-001"
        assert data["session"]["current_stage"] == 1

    def test_get_session_route(self, client):
        """Test getting a session via API."""
        # First create it
        client.post("/api/sessions/create", json={"session_id": "api-test-002"})
        # Then get it
        response = client.get("/api/sessions/api-test-002")
        assert response.status_code == 200
        data = response.json()
        assert data["session"]["session_id"] == "api-test-002"

    def test_get_nonexistent_session_route(self, client):
        """Test getting a nonexistent session."""
        response = client.get("/api/sessions/nonexistent")
        assert response.status_code == 404

    def test_delete_session_route(self, client):
        """Test deleting a session via API."""
        client.post("/api/sessions/create", json={"session_id": "api-test-003"})
        response = client.delete("/api/sessions/api-test-003")
        assert response.status_code == 200
        assert response.json()["deleted"] is True

    def test_next_stage_route(self, client):
        """Test advancing stage via API."""
        client.post("/api/sessions/create", json={"session_id": "api-test-004"})
        response = client.post(
            "/api/sessions/next-stage",
            json={"session_id": "api-test-004"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["session"]["current_stage"] == 2

    def test_go_to_stage_route(self, client):
        """Test going to specific stage via API."""
        client.post("/api/sessions/create", json={"session_id": "api-test-005"})
        response = client.post("/api/sessions/api-test-005/stage/3")
        assert response.status_code == 200
        data = response.json()
        assert data["session"]["current_stage"] == 3

    def test_go_to_invalid_stage_route(self, client):
        """Test going to an invalid stage."""
        client.post("/api/sessions/create", json={"session_id": "api-test-006"})
        response = client.post("/api/sessions/api-test-006/stage/6")
        assert response.status_code == 400
