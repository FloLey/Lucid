"""Tests for Stage 3 - Image prompts to Images."""

import base64
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import container
from app.models.slide import Slide, SlideText
from tests.conftest import run_async

stage3_service = container.stage_images
project_manager = container.project_manager
image_service = container.image_service


@pytest.fixture
def client():
    """Create a test client."""
    project_manager.clear_all()
    return TestClient(app)


@pytest.fixture
def project_with_prompts():
    """Create a project with image prompts."""
    project_manager.clear_all()
    project = run_async(project_manager.create_project())
    project.shared_prompt_prefix = "Modern minimalist style"
    project.slides = [
        Slide(
            index=0,
            text=SlideText(title="Hook", body="Grab attention"),
            image_prompt="Warm sunset gradient background",
        ),
        Slide(
            index=1,
            text=SlideText(title="Point 1", body="First key point"),
            image_prompt="Cool blue abstract shapes",
        ),
        Slide(
            index=2,
            text=SlideText(title="Point 2", body="Second key point"),
            image_prompt="Green nature-inspired pattern",
        ),
    ]
    run_async(project_manager.update_project(project))
    return project


@pytest.fixture
def mock_image_service():
    """Mock the image service."""

    async def mock_generate(*args, **kwargs):
        return "iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mNk+M9Qz0AEYBxVSF+FABJADq3/"

    with patch.object(image_service, "generate_image", mock_generate):
        yield


class TestImageService:
    """Tests for ImageService."""

    def test_generate_placeholder(self):
        """Test placeholder image generation."""
        base64_data = image_service._generate_placeholder("Test prompt")
        assert base64_data is not None
        # Should be valid base64
        decoded = base64.b64decode(base64_data)
        # Should be PNG (starts with PNG signature)
        assert decoded[:8] == b"\x89PNG\r\n\x1a\n"

    def test_generate_different_placeholders(self):
        """Test that different prompts generate different placeholders."""
        img1 = image_service._generate_placeholder("Prompt A")
        img2 = image_service._generate_placeholder("Prompt B")
        # Different prompts should create different images
        assert img1 != img2

    def test_decode_encode_roundtrip(self):
        """Test decoding and re-encoding an image."""
        original = image_service._generate_placeholder("Test")
        decoded = image_service.decode_image(original)
        re_encoded = image_service.encode_image(decoded)
        # Re-decoding should work
        image_service.decode_image(re_encoded)


class TestStage3Service:
    """Tests for Stage3Service."""

    def test_generate_all_images(self, project_with_prompts, mock_image_service):
        """Test generating images for all slides."""
        project = run_async(
            stage3_service.generate_all_images(
                project_id=project_with_prompts.project_id
            )
        )
        assert project is not None
        for slide in project.slides:
            assert slide.background_image_url is not None
            # Images are now stored on disk; background_image_url is a file path
            assert slide.background_image_url.startswith("/images/")

    def test_generate_images_no_project(self, mock_image_service):
        """Test generating images with no project."""
        project_manager.clear_all()
        project = run_async(
            stage3_service.generate_all_images(project_id="nonexistent")
        )
        assert project is None

    def test_generate_images_fills_missing_prompts(self, mock_image_service):
        """Test that missing prompts are filled with defaults."""
        project_manager.clear_all()
        created = run_async(project_manager.create_project())
        created.slides = [
            Slide(index=0, text=SlideText(body="Content")),  # No prompt
        ]
        run_async(project_manager.update_project(created))

        result = run_async(
            stage3_service.generate_all_images(project_id=created.project_id)
        )
        assert result.slides[0].image_prompt is not None
        assert result.slides[0].background_image_url is not None

    def test_regenerate_image(self, project_with_prompts, mock_image_service):
        """Test regenerating a single image."""
        run_async(
            stage3_service.generate_all_images(
                project_id=project_with_prompts.project_id
            )
        )

        project = run_async(
            stage3_service.regenerate_image(
                project_id=project_with_prompts.project_id,
                slide_index=1,
            )
        )
        assert project is not None
        assert project.slides[1].background_image_url is not None

    def test_regenerate_image_invalid_index(
        self, project_with_prompts, mock_image_service
    ):
        """Test regenerating image with invalid index."""
        project = run_async(
            stage3_service.regenerate_image(
                project_id=project_with_prompts.project_id,
                slide_index=99,
            )
        )
        assert project is None

    def test_set_image_data(self, project_with_prompts):
        """Test setting image data directly."""
        custom_data = "custombase64imagedata"
        project = run_async(
            stage3_service.set_image_data(
                project_id=project_with_prompts.project_id,
                slide_index=0,
                image_data=custom_data,
            )
        )
        assert project is not None
        assert project.slides[0].background_image_url == custom_data

    def test_set_image_data_invalid_index(self, project_with_prompts):
        """Test setting image data with invalid index."""
        project = run_async(
            stage3_service.set_image_data(
                project_id=project_with_prompts.project_id,
                slide_index=99,
                image_data="test",
            )
        )
        assert project is None


class TestStage3Routes:
    """Tests for Stage 3 API routes."""

    def test_generate_images_route(self, client, mock_image_service):
        """Test the generate images endpoint."""
        created = run_async(project_manager.create_project())
        project_id = created.project_id
        created.slides = [
            Slide(index=0, text=SlideText(body="Content"), image_prompt="Test prompt"),
            Slide(
                index=1, text=SlideText(body="Content 2"), image_prompt="Test prompt 2"
            ),
        ]
        run_async(project_manager.update_project(created))

        response = client.post(
            "/api/stage-images/generate",
            json={"project_id": project_id},
        )
        assert response.status_code == 200
        data = response.json()
        assert "project" in data
        assert data["project"]["slides"][0]["background_image_url"] is not None

    def test_generate_images_no_project(self, client):
        """Test generate images with no project."""
        response = client.post(
            "/api/stage-images/generate",
            json={"project_id": "nonexistent"},
        )
        assert response.status_code == 404

    def test_regenerate_image_route(self, client, mock_image_service):
        """Test the regenerate image endpoint."""
        created = run_async(project_manager.create_project())
        project_id = created.project_id
        created.slides = [
            Slide(
                index=0,
                text=SlideText(body="Content"),
                image_prompt="Prompt",
                background_image_url="existing",
            ),
        ]
        run_async(project_manager.update_project(created))

        response = client.post(
            "/api/stage-images/regenerate",
            json={"project_id": project_id, "slide_index": 0},
        )
        assert response.status_code == 200

    def test_upload_image_route(self, client):
        """Test the upload/set image endpoint."""
        created = run_async(project_manager.create_project())
        project_id = created.project_id
        created.slides = [Slide(index=0, text=SlideText(body="Content"))]
        run_async(project_manager.update_project(created))

        response = client.post(
            "/api/stage-images/upload",
            json={
                "project_id": project_id,
                "slide_index": 0,
                "image_data": "custombase64data",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["project"]["slides"][0]["background_image_url"] == "custombase64data"

