"""Tests for Stage Style - Visual style proposal generation and selection."""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import container
from app.models.slide import Slide, SlideText
from tests.conftest import run_async

project_manager = container.project_manager
stage_style_service = container.stage_style


@pytest.fixture
def client():
    """Create a test client."""
    project_manager.clear_all()
    return TestClient(app)


@pytest.fixture
def project_with_slides():
    """Create a project with slides."""
    project_manager.clear_all()
    project = run_async(project_manager.create_project())
    project.draft_text = "Test draft content"
    project.slides = [
        Slide(index=0, text=SlideText(title="Slide 1", body="Content 1")),
        Slide(index=1, text=SlideText(title="Slide 2", body="Content 2")),
        Slide(index=2, text=SlideText(title="Slide 3", body="Content 3")),
    ]
    run_async(project_manager.update_project(project))
    return project


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
        return "iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mNk+M9Qz0AEYBxVSF+FABJADq3/"

    def mock_save_image_to_disk(base64_data):
        return "/images/mock-preview.png"

    with (
        patch.object(stage_style_service, "gemini_service") as mock_gemini,
        patch.object(stage_style_service, "image_service") as mock_image,
        patch.object(stage_style_service, "storage_service") as mock_storage,
    ):
        mock_gemini.generate_json = mock_generate_json
        mock_image.generate_image = mock_generate_image
        mock_storage.save_image_to_disk = mock_save_image_to_disk
        yield mock_gemini, mock_image


class TestStageStyleService:
    """Tests for StageStyleService."""

    def test_generate_proposals(self, project_with_slides, mock_gemini_and_image):
        """Test generating style proposals."""
        project = run_async(
            stage_style_service.generate_proposals(
                project_with_slides.project_id, num_proposals=3
            )
        )
        assert project is not None
        assert len(project.style_proposals) == 3
        assert (
            project.style_proposals[0].description
            == "Warm sunset tones with golden gradients"
        )
        assert project.style_proposals[0].preview_image == "/images/mock-preview.png"
        assert project.selected_style_proposal_index is None

    def test_generate_proposals_no_project(self, mock_gemini_and_image):
        """Test generating proposals with no project."""
        project_manager.clear_all()
        project = run_async(
            stage_style_service.generate_proposals("nonexistent")
        )
        assert project is None

    def test_select_proposal(self, project_with_slides, mock_gemini_and_image):
        """Test selecting a style proposal."""
        run_async(
            stage_style_service.generate_proposals(project_with_slides.project_id)
        )
        project = run_async(
            stage_style_service.select_proposal(project_with_slides.project_id, 1)
        )
        assert project is not None
        assert project.selected_style_proposal_index == 1
        assert project.shared_prompt_prefix == "Cool blue minimalist aesthetic"

    def test_select_invalid_proposal(self, project_with_slides, mock_gemini_and_image):
        """Test selecting an invalid proposal index."""
        run_async(
            stage_style_service.generate_proposals(project_with_slides.project_id)
        )
        project = run_async(
            stage_style_service.select_proposal(project_with_slides.project_id, 10)
        )
        assert project is None

    def test_select_proposal_no_project(self):
        """Test selecting proposal with no project."""
        project_manager.clear_all()
        project = run_async(
            stage_style_service.select_proposal("nonexistent", 0)
        )
        assert project is None


class TestStageStyleRoutes:
    """Tests for Stage Style API routes."""

    def test_generate_route(self, client, project_with_slides, mock_gemini_and_image):
        """Test the generate proposals endpoint."""
        response = client.post(
            "/api/stage-style/generate",
            json={
                "project_id": project_with_slides.project_id,
                "num_proposals": 3,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["project"]["style_proposals"]) == 3

    def test_select_route(self, client, project_with_slides, mock_gemini_and_image):
        """Test the select proposal endpoint."""
        client.post(
            "/api/stage-style/generate",
            json={
                "project_id": project_with_slides.project_id,
                "num_proposals": 3,
            },
        )
        response = client.post(
            "/api/stage-style/select",
            json={
                "project_id": project_with_slides.project_id,
                "proposal_index": 0,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["project"]["selected_style_proposal_index"] == 0

    def test_generate_no_project(self, client):
        """Test generating proposals with no project."""
        response = client.post(
            "/api/stage-style/generate",
            json={"project_id": "nonexistent"},
        )
        assert response.status_code == 404

