"""Tests for project management."""

from app.dependencies import container
from app.models.slide import Slide, SlideText
from tests.conftest import run_async

project_manager = container.project_manager


def _add_slides(project_id: str, n: int) -> None:
    """Helper: populate a project with *n* blank slides for reorder tests."""
    project = run_async(project_manager.get_project(project_id))
    project.slides = [Slide(index=i, text=SlideText(body=f"Slide {i}")) for i in range(n)]
    run_async(project_manager.update_project(project))


class TestProjectManager:
    """Tests for ProjectManager service."""

    def test_create_project(self):
        """Test creating a new project."""
        project = run_async(project_manager.create_project())
        assert project.project_id is not None
        assert project.current_stage == 1

    def test_create_project_single_slide(self):
        """Test creating a single-slide project."""
        project = run_async(
            project_manager.create_project(slide_count=1)
        )
        assert project.slide_count == 1

    def test_get_project(self):
        """Test getting a project."""
        created = run_async(project_manager.create_project())
        project = run_async(project_manager.get_project(created.project_id))
        assert project is not None
        assert project.project_id == created.project_id

    def test_get_nonexistent_project(self):
        """Test getting a project that doesn't exist."""
        project = run_async(project_manager.get_project("nonexistent"))
        assert project is None

    def test_delete_project(self):
        """Test deleting a project."""
        created = run_async(project_manager.create_project())
        assert run_async(project_manager.delete_project(created.project_id)) is True
        assert run_async(project_manager.get_project(created.project_id)) is None

    def test_delete_nonexistent_project(self):
        """Test deleting a nonexistent project."""
        assert run_async(project_manager.delete_project("nonexistent")) is False

    def test_advance_stage(self):
        """Test advancing to next stage."""
        created = run_async(project_manager.create_project())
        project = run_async(project_manager.advance_stage(created.project_id))
        assert project.current_stage == 2
        project = run_async(project_manager.advance_stage(created.project_id))
        assert project.current_stage == 3

    def test_advance_stage_max(self):
        """Test advancing past max stage (MAX_STAGES=6)."""
        created = run_async(project_manager.create_project())
        created.current_stage = 6
        run_async(project_manager.update_project(created))
        project = run_async(project_manager.advance_stage(created.project_id))
        assert project.current_stage == 6  # Should not go past MAX_STAGES

    def test_go_to_stage(self):
        """Test going to a specific stage."""
        created = run_async(project_manager.create_project())
        project = run_async(project_manager.go_to_stage(created.project_id, 3))
        assert project.current_stage == 3

    def test_list_projects(self):
        """Test listing projects."""
        run_async(project_manager.create_project())
        run_async(project_manager.create_project())
        projects = run_async(project_manager.list_projects())
        assert len(projects) == 2

    def test_rename_project(self):
        """Test renaming a project."""
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
        """Test going to an invalid stage (beyond MAX_STAGES=6)."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]
        response = client.post(f"/api/projects/{project_id}/goto-stage/7")
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

    # ------------------------------------------------------------------
    # prev_stage tests
    # ------------------------------------------------------------------

    def test_prev_stage_from_stage_2(self, client):
        """POST /prev-stage from stage 2 returns project at stage 1."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]
        # Advance to stage 2
        client.post(f"/api/projects/{project_id}/next-stage")
        stage2_check = client.get(f"/api/projects/{project_id}").json()
        assert stage2_check["project"]["current_stage"] == 2

        response = client.post(f"/api/projects/{project_id}/prev-stage")
        assert response.status_code == 200
        assert response.json()["project"]["current_stage"] == 1

    def test_prev_stage_at_stage_1_stays(self, client):
        """POST /prev-stage at stage 1 does not go below 1."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]
        # Project starts at stage 1
        response = client.post(f"/api/projects/{project_id}/prev-stage")
        assert response.status_code == 200
        assert response.json()["project"]["current_stage"] == 1

    def test_prev_stage_nonexistent_project(self, client):
        """POST /prev-stage for a non-existent project returns 404."""
        response = client.post("/api/projects/does-not-exist/prev-stage")
        assert response.status_code == 404

    def test_prev_stage_multiple_steps(self, client):
        """POST /prev-stage multiple times decrements stage correctly."""
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]
        # Advance to stage 4
        client.post(f"/api/projects/{project_id}/goto-stage/4")

        # Go back twice
        client.post(f"/api/projects/{project_id}/prev-stage")
        response = client.post(f"/api/projects/{project_id}/prev-stage")
        assert response.status_code == 200
        assert response.json()["project"]["current_stage"] == 2

    # ------------------------------------------------------------------
    # reorder_slides tests
    # ------------------------------------------------------------------

    def test_reorder_slides_valid_permutation(self, client):
        """POST /reorder with a valid permutation reorders slides."""
        n = 3
        create_resp = client.post("/api/projects/", json={})
        assert create_resp.status_code == 200
        project_id = create_resp.json()["project"]["project_id"]
        _add_slides(project_id, n)

        # Reverse the slide order: [2, 1, 0]
        reversed_order = list(range(n - 1, -1, -1))
        response = client.post(
            f"/api/projects/{project_id}/reorder",
            json={"new_order": reversed_order},
        )
        assert response.status_code == 200
        slides = response.json()["project"]["slides"]
        assert len(slides) == n
        # Slide indices should be re-assigned 0..n-1
        for i, slide in enumerate(slides):
            assert slide["index"] == i

    def test_reorder_slides_identity(self, client):
        """POST /reorder with identity permutation leaves slides unchanged."""
        n = 4
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]
        _add_slides(project_id, n)

        identity = list(range(n))
        response = client.post(
            f"/api/projects/{project_id}/reorder",
            json={"new_order": identity},
        )
        assert response.status_code == 200
        assert len(response.json()["project"]["slides"]) == n

    def test_reorder_slides_wrong_length(self, client):
        """POST /reorder with wrong number of indices returns 400."""
        n = 3
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]
        _add_slides(project_id, n)

        response = client.post(
            f"/api/projects/{project_id}/reorder",
            json={"new_order": [0]},  # Too short for n=3
        )
        assert response.status_code == 400

    def test_reorder_slides_duplicate_indices(self, client):
        """POST /reorder with duplicate indices returns 400."""
        n = 3
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]
        _add_slides(project_id, n)

        # All zeros — same length but duplicates
        duplicates = [0] * n
        response = client.post(
            f"/api/projects/{project_id}/reorder",
            json={"new_order": duplicates},
        )
        assert response.status_code == 400

    def test_reorder_slides_out_of_range_index(self, client):
        """POST /reorder with an out-of-range index returns 400."""
        n = 3
        create_resp = client.post("/api/projects/", json={})
        project_id = create_resp.json()["project"]["project_id"]
        _add_slides(project_id, n)

        # Replace last valid index with one far beyond range
        order = list(range(n - 1)) + [n + 99]
        response = client.post(
            f"/api/projects/{project_id}/reorder",
            json={"new_order": order},
        )
        assert response.status_code == 400

    def test_reorder_slides_nonexistent_project(self, client):
        """POST /reorder for a non-existent project returns 404."""
        response = client.post(
            "/api/projects/does-not-exist/reorder",
            json={"new_order": [0]},
        )
        assert response.status_code == 404
