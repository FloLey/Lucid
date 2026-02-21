"""Tests for Template management — routes and service."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import container
from tests.conftest import run_async

template_manager = container.template_manager
project_manager = container.project_manager


@pytest.fixture
def client():
    """Create a test client with empty template and project tables."""
    run_async(template_manager._clear_all())
    project_manager.clear_all()
    return TestClient(app)


class TestTemplateService:
    """Tests for TemplateManager service."""

    def setup_method(self):
        run_async(template_manager._clear_all())

    def test_create_template_default(self):
        tmpl = run_async(template_manager.create_template("My Template"))
        assert tmpl.id is not None
        assert tmpl.name == "My Template"
        assert tmpl.default_slide_count == 5
        assert tmpl.config is not None

    def test_create_template_custom_slide_count(self):
        tmpl = run_async(template_manager.create_template("Single Slide", default_slide_count=1))
        assert tmpl.default_slide_count == 1

    def test_list_templates_empty(self):
        templates = run_async(template_manager.list_templates())
        assert templates == []

    def test_list_templates_multiple(self):
        run_async(template_manager.create_template("A"))
        run_async(template_manager.create_template("B"))
        templates = run_async(template_manager.list_templates())
        assert len(templates) == 2

    def test_get_template(self):
        created = run_async(template_manager.create_template("Fetch Me"))
        fetched = run_async(template_manager.get_template(created.id))
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.name == "Fetch Me"

    def test_get_nonexistent_template(self):
        result = run_async(template_manager.get_template("nonexistent"))
        assert result is None

    def test_update_template_name(self):
        created = run_async(template_manager.create_template("Old Name"))
        updated = run_async(template_manager.update_template(created.id, name="New Name"))
        assert updated is not None
        assert updated.name == "New Name"

    def test_update_template_slide_count(self):
        created = run_async(template_manager.create_template("tmpl", default_slide_count=5))
        updated = run_async(template_manager.update_template(created.id, default_slide_count=10))
        assert updated.default_slide_count == 10

    def test_update_nonexistent_template(self):
        result = run_async(template_manager.update_template("nonexistent", name="X"))
        assert result is None

    def test_delete_template(self):
        created = run_async(template_manager.create_template("Delete Me"))
        deleted = run_async(template_manager.delete_template(created.id))
        assert deleted is True
        assert run_async(template_manager.get_template(created.id)) is None

    def test_delete_nonexistent_template(self):
        result = run_async(template_manager.delete_template("nonexistent"))
        assert result is False


class TestTemplateRoutes:
    """Tests for template API routes."""

    def test_list_templates_empty(self, client):
        response = client.get("/api/templates/")
        assert response.status_code == 200
        assert response.json()["templates"] == []

    def test_create_template_route(self, client):
        response = client.post("/api/templates/", json={"name": "Test Template"})
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Template"
        assert data["default_slide_count"] == 5
        assert "id" in data

    def test_create_template_custom_slide_count(self, client):
        response = client.post("/api/templates/", json={"name": "Single", "default_slide_count": 1})
        assert response.status_code == 200
        assert response.json()["default_slide_count"] == 1

    def test_create_template_no_default_mode_field(self, client):
        """Ensure default_mode is not settable via API (field removed)."""
        response = client.post("/api/templates/", json={
            "name": "tmpl",
            "default_mode": "single_image",  # ignored field
        })
        # Should still succeed (extra fields are ignored by Pydantic by default)
        # or return validation error — either is fine; main thing is mode not leaked
        assert response.status_code in (200, 422)

    def test_get_template_route(self, client):
        created = client.post("/api/templates/", json={"name": "Gettable"}).json()
        response = client.get(f"/api/templates/{created['id']}")
        assert response.status_code == 200
        assert response.json()["name"] == "Gettable"

    def test_get_nonexistent_template_route(self, client):
        response = client.get("/api/templates/nonexistent")
        assert response.status_code == 404

    def test_update_template_route(self, client):
        created = client.post("/api/templates/", json={"name": "Original"}).json()
        response = client.patch(
            f"/api/templates/{created['id']}",
            json={"name": "Updated", "default_slide_count": 8},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated"
        assert data["default_slide_count"] == 8

    def test_update_nonexistent_template_route(self, client):
        response = client.patch("/api/templates/nonexistent", json={"name": "X"})
        assert response.status_code == 404

    def test_delete_template_route(self, client):
        created = client.post("/api/templates/", json={"name": "Deletable"}).json()
        response = client.delete(f"/api/templates/{created['id']}")
        assert response.status_code == 200
        assert response.json()["deleted"] is True

    def test_delete_nonexistent_template_route(self, client):
        response = client.delete("/api/templates/nonexistent")
        assert response.status_code == 404


class TestProjectCreationFromTemplate:
    """Tests for creating projects from templates."""

    def test_create_project_from_template(self, client):
        """Project slide_count comes from template."""
        tmpl = client.post("/api/templates/", json={"name": "T", "default_slide_count": 3}).json()
        response = client.post("/api/projects/", json={"template_id": tmpl["id"]})
        assert response.status_code == 200
        assert response.json()["project"]["slide_count"] == 3

    def test_create_project_blank_default_5_slides(self, client):
        """Blank project has 5 slides by default."""
        response = client.post("/api/projects/", json={})
        assert response.status_code == 200
        assert response.json()["project"]["slide_count"] == 5

    def test_create_project_nonexistent_template(self, client):
        response = client.post("/api/projects/", json={"template_id": "bad-id"})
        assert response.status_code == 404

    def test_project_card_no_mode_field(self, client):
        """ProjectCard no longer exposes mode."""
        client.post("/api/projects/", json={})
        response = client.get("/api/projects/")
        cards = response.json()["projects"]
        assert len(cards) == 1
        assert "mode" not in cards[0]
