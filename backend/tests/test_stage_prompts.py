"""Tests for Stage 2 - Slide texts to Image prompts."""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import container
from app.models.slide import Slide, SlideText
from tests.conftest import run_async

stage2_service = container.stage_prompts
project_manager = container.project_manager


@pytest.fixture
def client():
    """Create a test client."""
    run_async(project_manager.clear_all())
    return TestClient(app)


@pytest.fixture
def project_with_slides():
    """Create a project with slides for testing."""
    run_async(project_manager.clear_all())
    project = run_async(project_manager.create_project())
    project.slides = [
        Slide(index=0, text=SlideText(title="Hook", body="Grab attention")),
        Slide(index=1, text=SlideText(title="Point 1", body="First key point")),
        Slide(index=2, text=SlideText(title="Point 2", body="Second key point")),
    ]
    run_async(project_manager.update_project(project))
    return project


@pytest.fixture
def mock_gemini():
    """Mock the Gemini service for Stage 2."""

    async def mock_generate_json(*args, **kwargs):
        return {"prompt": "Generated image prompt for slide"}

    with patch("app.dependencies.container.stage_prompts.gemini_service") as mock:
        mock.generate_json = mock_generate_json
        yield mock


class TestStage2Service:
    """Tests for Stage2Service."""

    def test_generate_all_prompts(self, project_with_slides, mock_gemini):
        """Test generating prompts for all slides."""
        project = run_async(
            stage2_service.generate_all_prompts(
                project_id=project_with_slides.project_id,
                image_style_instructions="Warm, inviting colors",
            )
        )
        assert project is not None
        assert project.image_style_instructions == "Warm, inviting colors"
        for slide in project.slides:
            assert slide.image_prompt is not None

    def test_generate_prompts_no_project(self, mock_gemini):
        """Test generating prompts with no project."""
        run_async(project_manager.clear_all())
        project = run_async(
            stage2_service.generate_all_prompts(project_id="nonexistent")
        )
        assert project is None

    def test_generate_prompts_no_slides(self, mock_gemini):
        """Test generating prompts with no slides."""
        run_async(project_manager.clear_all())
        created = run_async(project_manager.create_project())
        project = run_async(
            stage2_service.generate_all_prompts(project_id=created.project_id)
        )
        assert project is None

    def test_regenerate_prompt(self, project_with_slides, mock_gemini):
        """Test regenerating a single prompt."""
        run_async(
            stage2_service.generate_all_prompts(
                project_id=project_with_slides.project_id
            )
        )

        async def mock_single(*args, **kwargs):
            return {"prompt": "New regenerated prompt"}

        mock_gemini.generate_json = mock_single

        project = run_async(
            stage2_service.regenerate_prompt(
                project_id=project_with_slides.project_id,
                slide_index=1,
            )
        )
        assert project is not None
        assert project.slides[1].image_prompt == "New regenerated prompt"

    def test_regenerate_prompt_invalid_index(self, project_with_slides, mock_gemini):
        """Test regenerating prompt with invalid index."""
        project = run_async(
            stage2_service.regenerate_prompt(
                project_id=project_with_slides.project_id,
                slide_index=99,
            )
        )
        assert project is None

    def test_update_prompt(self, project_with_slides):
        """Test manually updating a prompt."""
        project = run_async(
            stage2_service.update_prompt(
                project_id=project_with_slides.project_id,
                slide_index=0,
                prompt="Custom image prompt",
            )
        )
        assert project is not None
        assert project.slides[0].image_prompt == "Custom image prompt"

    def test_update_prompt_invalid_index(self, project_with_slides):
        """Test updating prompt with invalid index."""
        project = run_async(
            stage2_service.update_prompt(
                project_id=project_with_slides.project_id,
                slide_index=99,
                prompt="Custom prompt",
            )
        )
        assert project is None

    def test_update_style_instructions(self, project_with_slides):
        """Test updating style instructions."""
        project = run_async(
            stage2_service.update_style_instructions(
                project_id=project_with_slides.project_id,
                style_instructions="Vintage, retro aesthetic",
            )
        )
        assert project is not None
        assert project.image_style_instructions == "Vintage, retro aesthetic"

    def test_update_style_no_project(self):
        """Test updating style with no project."""
        run_async(project_manager.clear_all())
        project = run_async(
            stage2_service.update_style_instructions(
                project_id="nonexistent",
                style_instructions="Test",
            )
        )
        assert project is None


class TestStage2Routes:
    """Tests for Stage 2 API routes."""

    def test_generate_prompts_route(self, client, mock_gemini):
        """Test the generate prompts endpoint."""
        created = run_async(project_manager.create_project())
        project_id = created.project_id
        created.slides = [
            Slide(index=0, text=SlideText(body="Test content 1")),
            Slide(index=1, text=SlideText(body="Test content 2")),
        ]
        run_async(project_manager.update_project(created))

        response = client.post(
            "/api/stage-prompts/generate",
            json={
                "project_id": project_id,
                "image_style_instructions": "Modern, clean style",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "project" in data
        assert data["project"]["slides"][0]["image_prompt"] is not None

    def test_generate_prompts_no_project(self, client):
        """Test generate prompts with no project."""
        response = client.post(
            "/api/stage-prompts/generate",
            json={"project_id": "nonexistent"},
        )
        assert response.status_code == 404

    def test_regenerate_prompt_route(self, client, mock_gemini):
        """Test the regenerate prompt endpoint."""
        created = run_async(project_manager.create_project())
        project_id = created.project_id
        created.slides = [
            Slide(index=0, text=SlideText(body="Content"), image_prompt="Original"),
            Slide(index=1, text=SlideText(body="Content 2"), image_prompt="Original 2"),
        ]
        run_async(project_manager.update_project(created))

        response = client.post(
            "/api/stage-prompts/regenerate",
            json={"project_id": project_id, "slide_index": 0},
        )
        assert response.status_code == 200

    def test_update_prompt_route(self, client):
        """Test the update prompt endpoint."""
        created = run_async(project_manager.create_project())
        project_id = created.project_id
        created.slides = [Slide(index=0, text=SlideText(body="Content"))]
        run_async(project_manager.update_project(created))

        response = client.post(
            "/api/stage-prompts/update",
            json={
                "project_id": project_id,
                "slide_index": 0,
                "prompt": "Custom image: sunset over mountains",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert (
            data["project"]["slides"][0]["image_prompt"]
            == "Custom image: sunset over mountains"
        )

    def test_update_style_route(self, client):
        """Test the update style endpoint."""
        created = run_async(project_manager.create_project())
        project_id = created.project_id

        response = client.post(
            "/api/stage-prompts/style",
            json={
                "project_id": project_id,
                "style_instructions": "Vibrant, energetic colors",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert (
            data["project"]["image_style_instructions"] == "Vibrant, energetic colors"
        )

