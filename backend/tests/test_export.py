"""Tests for Export service."""

import json
import zipfile
from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import container
from app.models.slide import Slide, SlideText
from tests.conftest import run_async

project_manager = container.project_manager
export_service = container.export_service
image_service = container.image_service


@pytest.fixture
def client():
    """Create a test client."""
    project_manager.clear_all()
    return TestClient(app)


@pytest.fixture
def sample_image_base64():
    """Create a sample image."""
    return image_service._generate_placeholder("Test image")


@pytest.fixture
def project_with_final_images(sample_image_base64):
    """Create a project with final images."""
    project_manager.clear_all()
    project = run_async(project_manager.create_project())
    project.draft_text = "This is my test draft for export"
    project.slides = [
        Slide(
            index=0,
            text=SlideText(title="Welcome", body="Let's get started!"),
            background_image_url=sample_image_base64,
            final_image_url=sample_image_base64,
        ),
        Slide(
            index=1,
            text=SlideText(title="Key Point", body="This is important."),
            background_image_url=sample_image_base64,
            final_image_url=sample_image_base64,
        ),
        Slide(
            index=2,
            text=SlideText(title="Conclusion", body="Take action now!"),
            background_image_url=sample_image_base64,
            final_image_url=sample_image_base64,
        ),
    ]
    run_async(project_manager.update_project(project))
    return project


class TestExportService:
    """Tests for ExportService."""

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        assert export_service._sanitize_filename("Hello World!") == "Hello_World"
        assert export_service._sanitize_filename("Test@#$%") == "Test"
        assert (
            export_service._sanitize_filename(
                "A very long title that should be truncated"
            )
            == "A_very_long_title_that_should"
        )

    def test_generate_filename_with_title(self):
        """Test filename generation with title."""
        filename = export_service._generate_filename(0, "My Slide Title")
        assert filename == "01_My_Slide_Title.png"

    def test_generate_filename_without_title(self):
        """Test filename generation without title."""
        filename = export_service._generate_filename(0, None)
        assert filename == "01_slide.png"

    def test_generate_filename_index(self):
        """Test filename index formatting."""
        assert export_service._generate_filename(9, "Test").startswith("10_")
        assert export_service._generate_filename(0, "Test").startswith("01_")

    def test_export_project(self, project_with_final_images):
        """Test exporting a full project."""
        zip_buffer = run_async(
            export_service.export_project(project_with_final_images.project_id)
        )
        assert zip_buffer is not None

        # Verify ZIP contents
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            names = zf.namelist()
            assert "metadata.json" in names
            assert "slide_texts.txt" in names
            # Should have 3 slide images
            slide_files = [n for n in names if n.startswith("slides/")]
            assert len(slide_files) == 3

    def test_export_project_metadata(self, project_with_final_images):
        """Test metadata in exported ZIP."""
        zip_buffer = run_async(
            export_service.export_project(project_with_final_images.project_id)
        )

        with zipfile.ZipFile(zip_buffer, "r") as zf:
            metadata_content = zf.read("metadata.json")
            metadata = json.loads(metadata_content)

            assert metadata["project_id"] == project_with_final_images.project_id
            assert metadata["num_slides"] == 3
            assert len(metadata["slides"]) == 3
            assert metadata["slides"][0]["title"] == "Welcome"

    def test_export_project_text_file(self, project_with_final_images):
        """Test text content file in exported ZIP."""
        zip_buffer = run_async(
            export_service.export_project(project_with_final_images.project_id)
        )

        with zipfile.ZipFile(zip_buffer, "r") as zf:
            text_content = zf.read("slide_texts.txt").decode("utf-8")

            assert "Lucid Carousel Export" in text_content
            assert "Welcome" in text_content
            assert "Take action now!" in text_content

    def test_export_project_no_project(self):
        """Test export with no project."""
        project_manager.clear_all()
        zip_buffer = run_async(export_service.export_project("nonexistent"))
        assert zip_buffer is None

    def test_export_single_slide(self, project_with_final_images):
        """Test exporting a single slide."""
        image_buffer = run_async(
            export_service.export_single_slide(
                project_with_final_images.project_id, 0
            )
        )
        assert image_buffer is not None

        # Should be valid PNG
        content = image_buffer.read()
        assert content[:8] == b"\x89PNG\r\n\x1a\n"

    def test_export_single_slide_invalid_index(self, project_with_final_images):
        """Test export with invalid slide index."""
        image_buffer = run_async(
            export_service.export_single_slide(
                project_with_final_images.project_id, 99
            )
        )
        assert image_buffer is None


class TestExportRoutes:
    """Tests for Export API routes."""

    def test_export_zip_route(self, client, project_with_final_images):
        """Test the ZIP export endpoint."""
        response = client.post(
            "/api/export/zip",
            json={"project_id": project_with_final_images.project_id},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert "attachment" in response.headers["content-disposition"]

        # Verify it's a valid ZIP
        zip_buffer = BytesIO(response.content)
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            assert "metadata.json" in zf.namelist()

    def test_export_zip_get_route(self, client, project_with_final_images):
        """Test the GET ZIP export endpoint."""
        project_id = project_with_final_images.project_id
        response = client.get(f"/api/export/zip/{project_id}")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"

    def test_export_zip_no_project(self, client):
        """Test ZIP export with no project."""
        response = client.post(
            "/api/export/zip",
            json={"project_id": "nonexistent"},
        )
        assert response.status_code == 404

    def test_export_slide_route(self, client, project_with_final_images):
        """Test the single slide export endpoint."""
        response = client.post(
            "/api/export/slide",
            json={
                "project_id": project_with_final_images.project_id,
                "slide_index": 0,
            },
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert "slide_01.png" in response.headers["content-disposition"]

    def test_export_slide_get_route(self, client, project_with_final_images):
        """Test the GET single slide export endpoint."""
        project_id = project_with_final_images.project_id
        response = client.get(f"/api/export/slide/{project_id}/0")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"

    def test_export_slide_invalid_index(self, client, project_with_final_images):
        """Test slide export with invalid index."""
        response = client.post(
            "/api/export/slide",
            json={
                "project_id": project_with_final_images.project_id,
                "slide_index": 99,
            },
        )
        assert response.status_code == 404

