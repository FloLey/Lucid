"""Tests for /api/projects routes."""

import pytest


# ── Helpers ────────────────────────────────────────────────────────────────


def _create_project(client) -> dict:
    """Create a project and return the project dict."""
    resp = client.post("/api/projects/", json={})
    assert resp.status_code == 200
    return resp.json()["project"]


def _pid(project: dict) -> str:
    return project["project_id"]


# ── List & Create ──────────────────────────────────────────────────────────


class TestListAndCreate:
    def test_list_empty(self, client):
        resp = client.get("/api/projects/")
        assert resp.status_code == 200
        assert resp.json()["projects"] == []

    def test_create_returns_project_with_id(self, client):
        project = _create_project(client)
        assert "project_id" in project
        assert project["project_id"]

    def test_create_appears_in_list(self, client):
        project = _create_project(client)
        resp = client.get("/api/projects/")
        ids = [p["project_id"] for p in resp.json()["projects"]]
        assert _pid(project) in ids

    def test_create_multiple_projects(self, client):
        _create_project(client)
        _create_project(client)
        resp = client.get("/api/projects/")
        assert len(resp.json()["projects"]) == 2


# ── Get ────────────────────────────────────────────────────────────────────


class TestGetProject:
    def test_get_existing_project(self, client):
        project = _create_project(client)
        resp = client.get(f"/api/projects/{_pid(project)}")
        assert resp.status_code == 200
        assert resp.json()["project"]["project_id"] == _pid(project)

    def test_get_nonexistent_returns_404(self, client):
        resp = client.get("/api/projects/does-not-exist")
        assert resp.status_code == 404


# ── Delete ─────────────────────────────────────────────────────────────────


class TestDeleteProject:
    def test_delete_existing_project(self, client):
        project = _create_project(client)
        resp = client.delete(f"/api/projects/{_pid(project)}")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

    def test_delete_removes_from_list(self, client):
        project = _create_project(client)
        client.delete(f"/api/projects/{_pid(project)}")
        resp = client.get("/api/projects/")
        ids = [p["project_id"] for p in resp.json()["projects"]]
        assert _pid(project) not in ids

    def test_delete_nonexistent_returns_404(self, client):
        resp = client.delete("/api/projects/does-not-exist")
        assert resp.status_code == 404


# ── Rename ─────────────────────────────────────────────────────────────────


class TestRenameProject:
    def test_rename_updates_name(self, client):
        project = _create_project(client)
        resp = client.patch(
            f"/api/projects/{_pid(project)}/name", json={"name": "New Name"}
        )
        assert resp.status_code == 200
        assert resp.json()["project"]["name"] == "New Name"

    def test_rename_nonexistent_returns_404(self, client):
        resp = client.patch("/api/projects/does-not-exist/name", json={"name": "x"})
        assert resp.status_code == 404


# ── Stage navigation ───────────────────────────────────────────────────────


class TestStageNavigation:
    def test_next_stage_advances(self, client):
        project = _create_project(client)
        initial_stage = project["current_stage"]
        resp = client.post(f"/api/projects/{_pid(project)}/next-stage")
        assert resp.status_code == 200
        assert resp.json()["project"]["current_stage"] == initial_stage + 1

    def test_prev_stage_goes_back(self, client):
        project = _create_project(client)
        client.post(f"/api/projects/{_pid(project)}/next-stage")
        resp = client.post(f"/api/projects/{_pid(project)}/prev-stage")
        assert resp.status_code == 200
        assert resp.json()["project"]["current_stage"] == project["current_stage"]

    def test_goto_stage_valid(self, client):
        project = _create_project(client)
        resp = client.post(f"/api/projects/{_pid(project)}/goto-stage/3")
        assert resp.status_code == 200
        assert resp.json()["project"]["current_stage"] == 3

    def test_goto_stage_zero_returns_400(self, client):
        project = _create_project(client)
        resp = client.post(f"/api/projects/{_pid(project)}/goto-stage/0")
        assert resp.status_code == 400

    def test_goto_stage_out_of_range_returns_400(self, client):
        project = _create_project(client)
        resp = client.post(f"/api/projects/{_pid(project)}/goto-stage/99")
        assert resp.status_code == 400


# ── Reorder slides ─────────────────────────────────────────────────────────


class TestReorderSlides:
    def test_reorder_valid(self, client):
        project = _create_project(client)
        slide_count = len(project["slides"])
        new_order = list(reversed(range(slide_count)))
        resp = client.post(
            f"/api/projects/{_pid(project)}/reorder", json={"new_order": new_order}
        )
        assert resp.status_code == 200

    def test_reorder_wrong_length_returns_400(self, client):
        project = _create_project(client)
        resp = client.post(
            f"/api/projects/{_pid(project)}/reorder", json={"new_order": [0]}
        )
        assert resp.status_code == 400

    def test_reorder_nonexistent_project_returns_404(self, client):
        resp = client.post(
            "/api/projects/does-not-exist/reorder", json={"new_order": [0, 1, 2]}
        )
        assert resp.status_code == 404
