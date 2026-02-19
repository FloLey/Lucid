"""Tests for project management."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import container
from tests.conftest import run_async

project_manager = container.project_manager


@pytest.fixture
def client():
    """Create a test client."""
    project_manager.clear_all()
    return TestClient(app)


class TestProjectManager:
    """Tests for ProjectManager service."""

    def test_create_project(self):
        """Test creating a new project."""
        project_manager.clear_all()
        project = run_async(project_manager.create_project())
        assert project.project_id is not None
        assert project.current_stage == 1
        assert project.mode == "carousel"

    def test_create_project_single_image(self):
        """Test creating a single-image project."""
        project_manager.clear_all()
        project = run_async(
            project_manager.create_project(mode="single_image", slide_count=1)
        )
        assert project.mode == "single_image"
        assert project.slide_count == 1

    def test_get_project(self):
        """Test getting a project."""
        project_manager.clear_all()
        created = run_async(project_manager.create_project())
        project = run_async(project_manager.get_project(created.project_id))
        assert project is not None
        assert project.project_id == created.project_id

    def test_get_nonexistent_project(self):
        """Test getting a project that doesn't exist."""
        project_manager.clear_all()
        project = run_async(project_manager.get_project("nonexistent"))
        assert project is None

    def test_delete_project(self):
        """Test deleting a project."""
        project_manager.clear_all()
        created = run_async(project_manager.create_project())
        assert run_async(project_manager.delete_project(created.project_id)) is True
        assert run_async(project_manager.get_project(created.project_id)) is None

    def test_delete_nonexistent_project(self):
        """Test deleting a nonexistent project."""
        project_manager.clear_all()
        assert run_async(project_manager.delete_project("nonexistent")) is False

    def test_advance_stage(self):
        """Test advancing to next stage."""
        project_manager.clear_all()
        created = run_async(project_manager.create_project())
        project = run_async(project_manager.advance_stage(created.project_id))
        assert project.current_stage == 2
        project = run_async(project_manager.advance_stage(created.project_id))
        assert project.current_stage == 3

    def test_advance_stage_max(self):
        """Test advancing past max stage."""
        project_manager.clear_all()
        created = run_async(project_manager.create_project())
        created.current_stage = 5
        run_async(project_manager.update_project(created))
        project = run_async(project_manager.advance_stage(created.project_id))
        assert project.current_stage == 5  # Should not go past 5

    def test_go_to_stage(self):
        """Test going to a specific stage."""
        project_manager.clear_all()
        created = run_async(project_manager.create_project())
        project = run_async(project_manager.go_to_stage(created.project_id, 3))
        assert project.current_stage == 3

    def test_list_projects(self):
        """Test listing projects."""
        project_manager.clear_all()
        run_async(project_manager.create_project())
        run_async(project_manager.create_project())
        projects = run_async(project_manager.list_projects())
        assert len(projects) == 2

    def test_rename_project(self):
        """Test renaming a project."""
        project_manager.clear_all()
        created = run_async(project_manager.create_project())
        project = run_async(
            project_manager.rename_project(created.project_id, "New Name")
        )
        assert project.name == "New Name"


class TestProjectRoutes:
    """Tests for project API routes."""

    def test_list_projects_empty(self, client):
        """Test listing projects when empty."""
        response = client.get("/api/projects/")
        assert response.status_code == 200
        assert response.json()["projects"] == []

    def test_create_project_route(self, client):
        """Test creating a project via API."""
        response = client.post("/api/projects/", json={})
        assert response.status_code == 200
        data = response.json()
        assert "project" in data
        assert data["project"]["project_id"] is not None
        assert data["project"]["current_stage"] == 1

    def test_get_project_route(self, client):
        """Test getting a project via API."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]
        response = client.get(f"/api/projects/{project_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["project"]["project_id"] == project_id

    def test_get_nonexistent_project_route(self, client):
        """Test getting a nonexistent project."""
        response = client.get("/api/projects/nonexistent")
        assert response.status_code == 404

    def test_delete_project_route(self, client):
        """Test deleting a project via API."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]
        response = client.delete(f"/api/projects/{project_id}")
        assert response.status_code == 200
        assert response.json()["deleted"] is True

    def test_next_stage_route(self, client):
        """Test advancing stage via API."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]
        response = client.post(f"/api/projects/{project_id}/next-stage")
        assert response.status_code == 200
        data = response.json()
        assert data["project"]["current_stage"] == 2

    def test_goto_stage_route(self, client):
        """Test going to specific stage via API."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]
        response = client.post(f"/api/projects/{project_id}/goto-stage/3")
        assert response.status_code == 200
        data = response.json()
        assert data["project"]["current_stage"] == 3

    def test_goto_invalid_stage_route(self, client):
        """Test going to an invalid stage."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]
        response = client.post(f"/api/projects/{project_id}/goto-stage/6")
        assert response.status_code == 400

    def test_rename_project_route(self, client):
        """Test renaming a project via API."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]
        response = client.patch(
            f"/api/projects/{project_id}/name",
            json={"name": "My New Project"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["project"]["name"] == "My New Project"
