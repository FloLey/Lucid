"""Tests for Stage Draft - Draft to Slide texts."""

import pytest
from unittest.mock import patch, AsyncMock

from app.dependencies import container
from app.models.slide import Slide, SlideText
from tests.conftest import run_async

stage1_service = container.stage_draft
project_manager = container.project_manager


@pytest.fixture
def mock_gemini():
    """Mock the Gemini service to return predictable results."""

    async def mock_generate_json(*args, **kwargs):
        return {
            "slides": [
                {"title": "Slide 1", "body": "Content 1"},
                {"title": "Slide 2", "body": "Content 2"},
                {"title": "Slide 3", "body": "Content 3"},
                {"title": "Slide 4", "body": "Content 4"},
                {"title": "Slide 5", "body": "Content 5"},
            ]
        }

    with patch("app.dependencies.container.stage_draft.gemini_service") as mock:
        mock.generate_json = mock_generate_json
        yield mock


class TestStage1Service:
    """Tests for Stage1Service."""

    def test_generate_slide_texts_creates_slides(self, mock_gemini):
        """Test that generate_slide_texts populates slides on a project."""
        created = run_async(project_manager.create_project())
        project = run_async(
            stage1_service.generate_slide_texts(
                project_id=created.project_id,
                draft_text="This is a test draft about productivity tips.",
                num_slides=3,
                include_titles=True,
            )
        )
        assert project is not None
        assert project.project_id == created.project_id
        assert len(project.slides) == 3

    def test_generate_slide_texts_stores_inputs(self, mock_gemini):
        """Test that inputs are stored in project."""
        created = run_async(project_manager.create_project())
        project = run_async(
            stage1_service.generate_slide_texts(
                project_id=created.project_id,
                draft_text="Test draft content",
                num_slides=5,
                include_titles=False,
                additional_instructions="Make it funny",
            )
        )
        assert project.draft_text == "Test draft content"
        assert project.num_slides == 5
        assert project.include_titles is False
        assert project.additional_instructions == "Make it funny"

    def test_generate_slide_texts_with_titles(self, mock_gemini):
        """Test slide generation with titles."""
        created = run_async(project_manager.create_project())
        project = run_async(
            stage1_service.generate_slide_texts(
                project_id=created.project_id,
                draft_text="Test content for slides",
                num_slides=3,
                include_titles=True,
            )
        )
        # All slides should have content
        for slide in project.slides:
            assert slide.text.title is not None or slide.text.body != ""

    def test_generate_slide_texts_nonexistent_project(self, mock_gemini):
        """Test that generate_slide_texts returns None for nonexistent project."""
        result = run_async(
            stage1_service.generate_slide_texts(
                project_id="nonexistent",
                draft_text="Test draft",
                num_slides=3,
            )
        )
        assert result is None

    def test_regenerate_all_requires_draft(self, mock_gemini):
        """Test that regenerate_all requires existing draft."""
        created = run_async(project_manager.create_project())
        result = run_async(
            stage1_service.regenerate_all_slide_texts(created.project_id)
        )
        assert result is None  # No draft stored

    def test_regenerate_single_slide(self, mock_gemini):
        """Test regenerating a single slide."""
        created = run_async(project_manager.create_project())
        run_async(
            stage1_service.generate_slide_texts(
                project_id=created.project_id,
                draft_text="Test content",
                num_slides=3,
            )
        )

        project = run_async(
            stage1_service.regenerate_slide_text(
                project_id=created.project_id,
                slide_index=1,
            )
        )
        assert project is not None
        assert len(project.slides) == 3

    def test_update_slide_text(self):
        """Test manually updating slide text."""
        created = run_async(project_manager.create_project())
        created.slides = [Slide(index=0)]
        run_async(project_manager.update_project(created))

        result = run_async(
            stage1_service.update_slide_text(
                project_id=created.project_id,
                slide_index=0,
                title="New Title",
                body="New Body",
            )
        )
        assert result is not None
        assert result.slides[0].text.title == "New Title"
        assert result.slides[0].text.body == "New Body"

    def test_update_slide_text_partial(self):
        """Test partially updating slide text."""
        created = run_async(project_manager.create_project())
        created.slides = [
            Slide(index=0, text=SlideText(title="Original", body="Original body"))
        ]
        run_async(project_manager.update_project(created))

        result = run_async(
            stage1_service.update_slide_text(
                project_id=created.project_id,
                slide_index=0,
                body="Updated body only",
            )
        )
        assert result.slides[0].text.title == "Original"  # Unchanged
        assert result.slides[0].text.body == "Updated body only"

    def test_update_nonexistent_slide(self):
        """Test updating a nonexistent slide."""
        created = run_async(project_manager.create_project())
        result = run_async(
            stage1_service.update_slide_text(
                project_id=created.project_id,
                slide_index=99,
                body="New content",
            )
        )
        assert result is None

    def test_generate_slide_texts_gemini_failure_does_not_persist(self):
        """If Gemini raises during slide generation, the original slides are not overwritten."""
        created = run_async(project_manager.create_project())
        from app.models.slide import Slide, SlideText
        created.slides = [Slide(index=0, text=SlideText(body="Original content"))]
        run_async(project_manager.update_project(created))

        async def mock_generate_json_fail(*args, **kwargs):
            raise Exception("Gemini down")

        with patch("app.dependencies.container.stage_draft.gemini_service") as mock:
            mock.generate_json = mock_generate_json_fail
            with pytest.raises(Exception, match="Gemini down"):
                run_async(
                    stage1_service.generate_slide_texts(
                        project_id=created.project_id,
                        draft_text="A draft that triggers an error",
                    )
                )

        # Project state should be unchanged in the DB
        reloaded = run_async(project_manager.get_project(created.project_id))
        assert reloaded is not None
        assert len(reloaded.slides) == 1
        assert reloaded.slides[0].text.body == "Original content"


class TestStage1Routes:
    """Tests for Stage 1 API routes."""

    def test_generate_slide_texts_route(self, client, mock_gemini):
        """Test the generate slide texts endpoint."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]

        response = client.post(
            "/api/stage-draft/generate",
            json={
                "project_id": project_id,
                "draft_text": "This is my draft about social media tips.",
                "num_slides": 4,
                "include_titles": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "project" in data
        assert data["project"]["project_id"] == project_id
        assert len(data["project"]["slides"]) == 4

    def test_generate_slide_texts_validation(self, client):
        """Test input validation for generate endpoint."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]

        response = client.post(
            "/api/stage-draft/generate",
            json={
                "project_id": project_id,
                "draft_text": "",
                "num_slides": 5,
            },
        )
        assert response.status_code == 422  # Validation error

    def test_generate_slide_texts_num_slides_bounds(self, client):
        """Test num_slides bounds validation."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]

        response = client.post(
            "/api/stage-draft/generate",
            json={
                "project_id": project_id,
                "draft_text": "Test draft",
                "num_slides": 25,  # Max is 20
            },
        )
        assert response.status_code == 422

    def test_generate_slide_texts_num_slides_zero(self, client):
        """Test that num_slides=0 returns 422 (must be >= 1)."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]

        response = client.post(
            "/api/stage-draft/generate",
            json={
                "project_id": project_id,
                "draft_text": "Test draft",
                "num_slides": 0,
            },
        )
        assert response.status_code == 422

    def test_generate_slide_texts_whitespace_only_draft(self, client):
        """Whitespace-only draft_text is not rejected at the route level (min_length only
        checks raw length) and is forwarded to the service. The service will attempt a
        Gemini call; without a mocked API key it returns 503 (GeminiError). Accepted
        statuses cover both the no-API-key (503) and any future validation (422/400)."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]

        response = client.post(
            "/api/stage-draft/generate",
            json={
                "project_id": project_id,
                "draft_text": "   ",
            },
        )
        # Without a mocked Gemini service, a whitespace draft causes a GeminiError (503).
        # If server-side validation is added later, 422/400 are also acceptable.
        assert response.status_code in (422, 400, 404, 503)

    def test_regenerate_all_route(self, client, mock_gemini):
        """Test regenerate all endpoint."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]

        client.post(
            "/api/stage-draft/generate",
            json={
                "project_id": project_id,
                "draft_text": "Original draft content",
                "num_slides": 3,
            },
        )
        response = client.post(
            "/api/stage-draft/regenerate-all",
            json={"project_id": project_id},
        )
        assert response.status_code == 200
        assert len(response.json()["project"]["slides"]) == 3

    def test_regenerate_all_no_draft(self, client):
        """Test regenerate all without prior generation."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]

        response = client.post(
            "/api/stage-draft/regenerate-all",
            json={"project_id": project_id},
        )
        assert response.status_code == 404

    def test_regenerate_single_route(self, client, mock_gemini):
        """Test regenerate single slide endpoint."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]

        client.post(
            "/api/stage-draft/generate",
            json={
                "project_id": project_id,
                "draft_text": "Test content for slides",
                "num_slides": 3,
            },
        )
        response = client.post(
            "/api/stage-draft/regenerate",
            json={"project_id": project_id, "slide_index": 1},
        )
        assert response.status_code == 200

    def test_update_slide_route(self, client, mock_gemini):
        """Test update slide text endpoint."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]

        client.post(
            "/api/stage-draft/generate",
            json={
                "project_id": project_id,
                "draft_text": "Test content",
                "num_slides": 2,
            },
        )
        response = client.post(
            "/api/stage-draft/update",
            json={
                "project_id": project_id,
                "slide_index": 0,
                "title": "Custom Title",
                "body": "Custom body content",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["project"]["slides"][0]["text"]["title"] == "Custom Title"
        assert data["project"]["slides"][0]["text"]["body"] == "Custom body content"


class TestWordsPerSlide:
    """Tests for words_per_slide parameter."""

    def test_keep_as_is_skips_ai(self, client):
        """keep_as_is uses draft text directly — no Gemini call."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]

        # No mock_gemini fixture — keep_as_is must not call Gemini
        response = client.post(
            "/api/stage-draft/generate",
            json={
                "project_id": project_id,
                "draft_text": "This is my draft text.",
                "words_per_slide": "keep_as_is",
            },
        )
        assert response.status_code == 200
        data = response.json()
        slides = data["project"]["slides"]
        assert len(slides) == 1
        assert slides[0]["text"]["body"] == "This is my draft text."

    def test_keep_as_is_returns_one_slide(self, client):
        """keep_as_is always produces exactly 1 slide."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]

        response = client.post(
            "/api/stage-draft/generate",
            json={
                "project_id": project_id,
                "draft_text": "Draft content here.",
                "num_slides": 5,  # ignored when keep_as_is
                "words_per_slide": "keep_as_is",
            },
        )
        assert response.status_code == 200
        assert len(response.json()["project"]["slides"]) == 1

    def test_words_per_slide_short_accepted(self, client, mock_gemini):
        """'short' is accepted and generation proceeds normally."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]

        response = client.post(
            "/api/stage-draft/generate",
            json={
                "project_id": project_id,
                "draft_text": "Draft content.",
                "num_slides": 3,
                "words_per_slide": "short",
            },
        )
        assert response.status_code == 200
        assert len(response.json()["project"]["slides"]) == 3

    def test_words_per_slide_medium_accepted(self, client, mock_gemini):
        """'medium' is accepted and generation proceeds normally."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]

        response = client.post(
            "/api/stage-draft/generate",
            json={
                "project_id": project_id,
                "draft_text": "Draft content.",
                "num_slides": 3,
                "words_per_slide": "medium",
            },
        )
        assert response.status_code == 200

    def test_words_per_slide_long_accepted(self, client, mock_gemini):
        """'long' is accepted and generation proceeds normally."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]

        response = client.post(
            "/api/stage-draft/generate",
            json={
                "project_id": project_id,
                "draft_text": "Draft content.",
                "num_slides": 2,
                "words_per_slide": "long",
            },
        )
        assert response.status_code == 200

    def test_words_per_slide_none_uses_ai_default(self, client, mock_gemini):
        """Omitting words_per_slide works (defaults to None / AI decides)."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]

        response = client.post(
            "/api/stage-draft/generate",
            json={
                "project_id": project_id,
                "draft_text": "Draft content.",
                "num_slides": 3,
            },
        )
        assert response.status_code == 200

    def test_build_word_count_instruction_short(self):
        """_build_word_count_instruction returns correct text for 'short'."""
        instr = stage1_service._build_word_count_instruction("short")
        assert "20" in instr and "50" in instr

    def test_build_word_count_instruction_medium(self):
        instr = stage1_service._build_word_count_instruction("medium")
        assert "50" in instr and "100" in instr

    def test_build_word_count_instruction_long(self):
        instr = stage1_service._build_word_count_instruction("long")
        assert "100" in instr and "200" in instr

    def test_build_word_count_instruction_ai(self):
        instr = stage1_service._build_word_count_instruction(None)
        assert "naturally" in instr.lower() or "requires" in instr.lower()

    def test_keep_as_is_service_direct(self):
        """Test keep_as_is path directly through the service."""
        created = run_async(project_manager.create_project())
        project = run_async(
            stage1_service.generate_slide_texts(
                project_id=created.project_id,
                draft_text="Keep this text.",
                words_per_slide="keep_as_is",
            )
        )
        assert project is not None
        assert len(project.slides) == 1
        assert project.slides[0].text.body == "Keep this text."


@pytest.fixture
def mock_title_gemini():
    """Mock Gemini to return a title for generate_project_title tests."""

    async def mock_generate_json(*args, **kwargs):
        return {"title": "Productivity Tips"}

    with patch("app.dependencies.container.stage_draft.gemini_service") as mock:
        mock.generate_json = mock_generate_json
        yield mock


class TestGenerateProjectTitle:
    """Tests for StageDraftService.generate_project_title."""

    def test_generate_title_sets_name(self, mock_title_gemini):
        """generate_project_title renames the project when slides exist."""
        created = run_async(project_manager.create_project())
        created.slides = [
            Slide(index=0, text=SlideText(title="Hook", body="Intro text")),
            Slide(index=1, text=SlideText(title="Tip 1", body="First tip content")),
        ]
        run_async(project_manager.update_project(created))

        result = run_async(
            stage1_service.generate_project_title(created.project_id, force=True)
        )
        assert result is not None
        assert result.name == "Productivity Tips"
        assert result.name_manually_set is False

    def test_generate_title_no_slides_returns_project_unchanged(self, mock_title_gemini):
        """generate_project_title returns project unchanged when there are no slides."""
        created = run_async(project_manager.create_project())

        result = run_async(
            stage1_service.generate_project_title(created.project_id, force=True)
        )
        assert result is not None
        assert result.name == created.name

    def test_generate_title_nonexistent_project_returns_none(self, mock_title_gemini):
        """generate_project_title returns None for a nonexistent project."""

        result = run_async(
            stage1_service.generate_project_title("nonexistent-id", force=True)
        )
        assert result is None

    def test_generate_title_skips_when_manually_set_without_force(self, mock_title_gemini):
        """generate_project_title skips when name was manually set and force=False."""
        created = run_async(project_manager.create_project())
        created.slides = [Slide(index=0, text=SlideText(body="Some content"))]
        created.name = "My Custom Name"
        created.name_manually_set = True
        run_async(project_manager.update_project(created))

        result = run_async(
            stage1_service.generate_project_title(created.project_id, force=False)
        )
        assert result is None

    def test_generate_title_skips_when_not_untitled_without_force(self, mock_title_gemini):
        """generate_project_title skips when name doesn't start with Untitled and force=False."""
        created = run_async(project_manager.create_project())
        created.slides = [Slide(index=0, text=SlideText(body="Some content"))]
        created.name = "Already Named Project"
        run_async(project_manager.update_project(created))

        result = run_async(
            stage1_service.generate_project_title(created.project_id, force=False)
        )
        assert result is None

    def test_generate_title_force_overrides_manually_set(self, mock_title_gemini):
        """generate_project_title renames even a manually-set name when force=True."""
        created = run_async(project_manager.create_project())
        created.slides = [Slide(index=0, text=SlideText(body="Some content"))]
        created.name = "Old Manual Name"
        created.name_manually_set = True
        run_async(project_manager.update_project(created))

        result = run_async(
            stage1_service.generate_project_title(created.project_id, force=True)
        )
        assert result is not None
        assert result.name == "Productivity Tips"

    def test_generate_title_gemini_failure_returns_none(self):
        """generate_project_title returns None gracefully when Gemini raises."""

        async def mock_generate_json_fail(*args, **kwargs):
            raise RuntimeError("Gemini unavailable")
        created = run_async(project_manager.create_project())
        created.slides = [Slide(index=0, text=SlideText(body="Some content"))]
        run_async(project_manager.update_project(created))

        with patch(
            "app.dependencies.container.stage_draft.gemini_service"
        ) as mock:
            mock.generate_json = mock_generate_json_fail
            result = run_async(
                stage1_service.generate_project_title(created.project_id, force=True)
            )
        assert result is None

    def test_generate_title_empty_response_leaves_name_unchanged(self):
        """generate_project_title leaves name unchanged when Gemini returns no title."""

        async def mock_generate_json_empty(*args, **kwargs):
            return {}
        created = run_async(project_manager.create_project())
        created.slides = [Slide(index=0, text=SlideText(body="Some content"))]
        run_async(project_manager.update_project(created))
        original_name = created.name

        with patch(
            "app.dependencies.container.stage_draft.gemini_service"
        ) as mock:
            mock.generate_json = mock_generate_json_empty
            result = run_async(
                stage1_service.generate_project_title(created.project_id, force=True)
            )
        assert result is not None
        assert result.name == original_name

    def test_generate_title_auto_runs_on_untitled_project(self, mock_title_gemini):
        """generate_project_title runs (force=False) when project name starts with Untitled."""
        created = run_async(project_manager.create_project())
        created.slides = [Slide(index=0, text=SlideText(body="Some content"))]
        run_async(project_manager.update_project(created))
        assert created.name.startswith("Untitled")

        result = run_async(
            stage1_service.generate_project_title(created.project_id, force=False)
        )
        assert result is not None
        assert result.name == "Productivity Tips"


class TestGenerateTitleRoute:
    """Tests for the POST /api/projects/{id}/generate-title route."""

    def test_generate_title_route_success(self, client, mock_title_gemini):
        """generate-title endpoint returns project with updated name."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]

        # Add slides directly via service so title generation proceeds
        proj = run_async(project_manager.get_project(project_id))
        proj.slides = [Slide(index=0, text=SlideText(body="Some content"))]
        run_async(project_manager.update_project(proj))

        response = client.post(f"/api/projects/{project_id}/generate-title")
        assert response.status_code == 200
        data = response.json()
        assert "project" in data
        assert data["project"]["name"] == "Productivity Tips"

    def test_generate_title_route_nonexistent_project(self, client):
        """generate-title returns 404 for unknown project."""
        response = client.post("/api/projects/nonexistent/generate-title")
        assert response.status_code == 404

    def test_generate_title_route_no_slides_returns_current_project(self, client, mock_title_gemini):
        """generate-title returns the project unchanged when it has no slides."""
        create_resp = client.post("/api/projects/", json={})
        project = create_resp.json()["project"]
        project_id = project["project_id"]
        original_name = project["name"]

        response = client.post(f"/api/projects/{project_id}/generate-title")
        assert response.status_code == 200
        assert response.json()["project"]["name"] == original_name

    def test_auto_naming_included_in_slide_generation_response(self, client, mock_title_gemini):
        """Slide generation response already includes the AI-generated project name."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]

        with patch("app.dependencies.container.stage_draft.gemini_service") as mock:
            mock.generate_json = AsyncMock(
                side_effect=[
                    {
                        "slides": [
                            {"title": "Slide 1", "body": "Content 1"},
                            {"title": "Slide 2", "body": "Content 2"},
                        ]
                    },
                    {"title": "Productivity Tips"},
                ]
            )
            response = client.post(
                "/api/stage-draft/generate",
                json={
                    "project_id": project_id,
                    "draft_text": "Tips for being productive.",
                    "num_slides": 2,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["project"]["name"] == "Productivity Tips"
        assert len(data["project"]["slides"]) == 2

    def test_auto_naming_skipped_for_manually_named_project(self, client):
        """Slide generation does not overwrite a manually-set project name."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]

        # Manually rename the project first
        client.patch(
            f"/api/projects/{project_id}/name",
            json={"name": "My Chosen Name"},
        )

        with patch("app.dependencies.container.stage_draft.gemini_service") as mock:
            mock.generate_json = AsyncMock(
                return_value={
                    "slides": [
                        {"title": "Slide 1", "body": "Content 1"},
                    ]
                }
            )
            response = client.post(
                "/api/stage-draft/generate",
                json={
                    "project_id": project_id,
                    "draft_text": "Some draft.",
                    "num_slides": 1,
                },
            )

        assert response.status_code == 200
        assert response.json()["project"]["name"] == "My Chosen Name"

