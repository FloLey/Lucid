"""Tests for the Concept Matrix Generator — models, DB, settings, and routes."""

from __future__ import annotations

import pytest
from pathlib import Path
from pydantic import ValidationError
from unittest.mock import patch

from app.dependencies import container
from app.models.matrix import (
    CreateMatrixRequest,
    MatrixSettings,
    RegenerateCellRequest,
)
from app.services.matrix_settings_manager import MatrixSettingsManager
from tests.conftest import run_async

matrix_db = container.matrix_db


# ── Helpers ───────────────────────────────────────────────────────────────


def _clear():
    """Clear all matrix data before a test."""
    run_async(matrix_db.clear_all())


# ── 1. Models ─────────────────────────────────────────────────────────────


class TestMatrixModels:
    """Pure Pydantic validation — no DB or network calls."""

    def test_matrix_settings_defaults(self):
        s = MatrixSettings()
        assert s.text_model == "gemini-2.5-flash"
        assert s.image_model == "gemini-2.5-flash-image"
        assert s.diagonal_temperature == pytest.approx(0.9)
        assert s.axes_temperature == pytest.approx(0.8)
        assert s.cell_temperature == pytest.approx(0.7)
        assert s.validation_temperature == pytest.approx(0.3)
        assert s.max_concurrency == 4
        assert s.max_retries == 3

    def test_create_request_theme_too_short(self):
        with pytest.raises(ValidationError):
            CreateMatrixRequest(theme="ab")

    def test_create_request_n_too_large(self):
        with pytest.raises(ValidationError):
            CreateMatrixRequest(theme="valid theme", n=9)

    def test_create_request_n_too_small(self):
        with pytest.raises(ValidationError):
            CreateMatrixRequest(theme="valid theme", n=1)

    def test_create_request_defaults(self):
        req = CreateMatrixRequest(theme="AI Ethics")
        assert req.n == 4
        assert req.language == "English"
        assert req.style_mode == "neutral"
        assert req.include_images is False
        assert req.name is None

    def test_create_request_custom_values(self):
        req = CreateMatrixRequest(
            theme="Cheese types",
            n=3,
            language="French",
            style_mode="fun",
            include_images=True,
            name="My Matrix",
        )
        assert req.n == 3
        assert req.language == "French"
        assert req.include_images is True

    def test_regenerate_cell_request_defaults(self):
        req = RegenerateCellRequest()
        assert req.image_only is False
        assert req.extra_instructions is None


# ── 2. MatrixDB ───────────────────────────────────────────────────────────


class TestMatrixDB:
    """CRUD operations against real test SQLite — no mocks."""

    def test_create_project_returns_project(self):
        _clear()
        p = run_async(matrix_db.create_project(
            theme="AI Ethics", n=3, language="English",
            style_mode="neutral", include_images=False,
        ))
        assert p.id is not None
        assert p.theme == "AI Ethics"
        assert p.n == 3
        assert p.status == "pending"

    def test_create_project_creates_n_squared_cells(self):
        _clear()
        p = run_async(matrix_db.create_project(
            theme="Test", n=3, language="English",
            style_mode="neutral", include_images=False,
        ))
        assert len(p.cells) == 9  # 3×3
        assert all(c.cell_status == "pending" for c in p.cells)

    def test_create_project_4x4_has_16_cells(self):
        _clear()
        p = run_async(matrix_db.create_project(
            theme="Test", n=4, language="English",
            style_mode="neutral", include_images=False,
        ))
        assert len(p.cells) == 16  # 4×4

    def test_get_project_includes_cells(self):
        _clear()
        created = run_async(matrix_db.create_project(
            theme="Test", n=2, language="English",
            style_mode="neutral", include_images=False,
        ))
        fetched = run_async(matrix_db.get_project(created.id))
        assert fetched is not None
        assert fetched.id == created.id
        assert len(fetched.cells) == 4  # 2×2

    def test_get_nonexistent_project(self):
        _clear()
        result = run_async(matrix_db.get_project("nonexistent-id"))
        assert result is None

    def test_list_projects_empty(self):
        _clear()
        cards = run_async(matrix_db.list_projects())
        assert cards == []

    def test_list_projects_returns_cards(self):
        _clear()
        run_async(matrix_db.create_project(
            theme="Cheese", n=3, language="English",
            style_mode="neutral", include_images=False,
        ))
        run_async(matrix_db.create_project(
            theme="Wine", n=2, language="French",
            style_mode="fun", include_images=True,
        ))
        cards = run_async(matrix_db.list_projects())
        assert len(cards) == 2
        # Cards are lightweight — no cells list attribute
        for card in cards:
            assert not hasattr(card, "cells")

    def test_delete_project(self):
        _clear()
        p = run_async(matrix_db.create_project(
            theme="Test", n=2, language="English",
            style_mode="neutral", include_images=False,
        ))
        deleted = run_async(matrix_db.delete_project(p.id))
        assert deleted is True
        assert run_async(matrix_db.get_project(p.id)) is None

    def test_delete_cascades_to_cells(self):
        _clear()
        p = run_async(matrix_db.create_project(
            theme="Test", n=2, language="English",
            style_mode="neutral", include_images=False,
        ))
        run_async(matrix_db.delete_project(p.id))
        cells = run_async(matrix_db.get_all_cells(p.id))
        assert cells == []

    def test_delete_nonexistent_project(self):
        _clear()
        result = run_async(matrix_db.delete_project("nonexistent-id"))
        assert result is False

    def test_upsert_cell_updates_label(self):
        _clear()
        p = run_async(matrix_db.create_project(
            theme="Test", n=2, language="English",
            style_mode="neutral", include_images=False,
        ))
        run_async(matrix_db.upsert_cell(p.id, row=0, col=0, label="Brie"))
        refreshed = run_async(matrix_db.get_project(p.id))
        diagonal_cell = next(c for c in refreshed.cells if c.row == 0 and c.col == 0)
        assert diagonal_cell.label == "Brie"

    def test_upsert_cell_updates_status(self):
        _clear()
        p = run_async(matrix_db.create_project(
            theme="Test", n=2, language="English",
            style_mode="neutral", include_images=False,
        ))
        run_async(matrix_db.upsert_cell(p.id, row=0, col=1, cell_status="complete"))
        refreshed = run_async(matrix_db.get_project(p.id))
        cell = next(c for c in refreshed.cells if c.row == 0 and c.col == 1)
        assert cell.cell_status == "complete"

    def test_update_project_status(self):
        _clear()
        p = run_async(matrix_db.create_project(
            theme="Test", n=2, language="English",
            style_mode="neutral", include_images=False,
        ))
        run_async(matrix_db.update_project_status(p.id, "generating"))
        refreshed = run_async(matrix_db.get_project(p.id))
        assert refreshed.status == "generating"

    def test_update_project_status_with_error(self):
        _clear()
        p = run_async(matrix_db.create_project(
            theme="Test", n=2, language="English",
            style_mode="neutral", include_images=False,
        ))
        run_async(matrix_db.update_project_status(p.id, "failed", "Something went wrong"))
        refreshed = run_async(matrix_db.get_project(p.id))
        assert refreshed.status == "failed"
        assert refreshed.error_message == "Something went wrong"

    def test_get_cell(self):
        _clear()
        p = run_async(matrix_db.create_project(
            theme="Test", n=3, language="English",
            style_mode="neutral", include_images=False,
        ))
        cell = run_async(matrix_db.get_cell(p.id, row=1, col=2))
        assert cell is not None
        assert cell.row == 1
        assert cell.col == 2
        assert cell.project_id == p.id

    def test_get_cell_nonexistent_project(self):
        _clear()
        cell = run_async(matrix_db.get_cell("nonexistent", row=0, col=0))
        assert cell is None


# ── 3. MatrixSettingsManager ──────────────────────────────────────────────


class TestMatrixSettingsManager:
    """Unit tests — uses a temp file path, no shared DB."""

    def test_get_returns_defaults_when_no_file(self, tmp_path):
        settings_file = tmp_path / "matrix_settings.json"
        mgr = MatrixSettingsManager(settings_file=settings_file)
        s = mgr.get()
        assert s == MatrixSettings()

    def test_update_persists(self, tmp_path):
        settings_file = tmp_path / "matrix_settings.json"
        mgr = MatrixSettingsManager(settings_file=settings_file)
        modified = MatrixSettings(max_concurrency=10, max_retries=5)
        mgr.update(modified)

        # Fresh instance reads the persisted values
        mgr2 = MatrixSettingsManager(settings_file=settings_file)
        s = mgr2.get()
        assert s.max_concurrency == 10
        assert s.max_retries == 5

    def test_reset_restores_defaults(self, tmp_path):
        settings_file = tmp_path / "matrix_settings.json"
        mgr = MatrixSettingsManager(settings_file=settings_file)
        mgr.update(MatrixSettings(max_concurrency=10, text_model="custom-model"))
        mgr.reset()
        s = mgr.get()
        assert s == MatrixSettings()


# ── 4. Routes ─────────────────────────────────────────────────────────────


@pytest.fixture
def mock_create(monkeypatch):
    """Patch create_and_start to skip background generation task."""
    async def _fake_start(req):
        p = await matrix_db.create_project(
            theme=req.theme,
            n=req.n,
            language=req.language,
            style_mode=req.style_mode,
            include_images=req.include_images,
            name=req.name,
        )
        await matrix_db.update_project_status(p.id, "generating")
        # Re-fetch so the returned project reflects the updated status
        return await matrix_db.get_project(p.id)

    monkeypatch.setattr(container.matrix_service, "create_and_start", _fake_start)


class TestMatrixRoutes:
    """HTTP route tests using FastAPI TestClient."""

    def setup_method(self):
        _clear()

    def test_list_matrices_empty(self, client):
        resp = client.get("/api/matrix/")
        assert resp.status_code == 200
        assert resp.json()["matrices"] == []

    def test_create_matrix(self, client, mock_create):
        resp = client.post("/api/matrix/", json={"theme": "AI Ethics", "n": 3})
        assert resp.status_code == 200
        data = resp.json()["matrix"]
        assert data["theme"] == "AI Ethics"
        assert data["n"] == 3
        assert data["status"] == "generating"
        assert data["id"] is not None

    def test_create_matrix_n_too_large(self, client, mock_create):
        # Pydantic validates n <= 8 before the route handler, returning 422
        resp = client.post("/api/matrix/", json={"theme": "AI Ethics", "n": 9})
        assert resp.status_code == 422

    def test_create_matrix_theme_too_short(self, client):
        resp = client.post("/api/matrix/", json={"theme": "ab"})
        assert resp.status_code == 422

    def test_list_matrices_after_create(self, client, mock_create):
        client.post("/api/matrix/", json={"theme": "Cheese types", "n": 2})
        resp = client.get("/api/matrix/")
        assert resp.status_code == 200
        assert len(resp.json()["matrices"]) == 1

    def test_get_matrix(self, client, mock_create):
        create_resp = client.post("/api/matrix/", json={"theme": "Test theme", "n": 2})
        matrix_id = create_resp.json()["matrix"]["id"]

        resp = client.get(f"/api/matrix/{matrix_id}")
        assert resp.status_code == 200
        assert resp.json()["matrix"]["id"] == matrix_id

    def test_get_matrix_not_found(self, client):
        resp = client.get("/api/matrix/nonexistent-id")
        assert resp.status_code == 404

    def test_get_matrix_has_cells(self, client, mock_create):
        create_resp = client.post("/api/matrix/", json={"theme": "Test theme", "n": 3})
        matrix_id = create_resp.json()["matrix"]["id"]

        resp = client.get(f"/api/matrix/{matrix_id}")
        assert resp.status_code == 200
        cells = resp.json()["matrix"]["cells"]
        assert len(cells) == 9  # 3×3

    def test_delete_matrix(self, client, mock_create):
        create_resp = client.post("/api/matrix/", json={"theme": "Delete me", "n": 2})
        matrix_id = create_resp.json()["matrix"]["id"]

        resp = client.delete(f"/api/matrix/{matrix_id}")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

        # Confirm gone
        assert client.get(f"/api/matrix/{matrix_id}").status_code == 404

    def test_delete_matrix_not_found(self, client):
        resp = client.delete("/api/matrix/nonexistent-id")
        assert resp.status_code == 404

    def test_cancel_not_generating(self, client, mock_create):
        create_resp = client.post("/api/matrix/", json={"theme": "Test", "n": 2})
        matrix_id = create_resp.json()["matrix"]["id"]

        # No background task was started (mock_create skips it)
        resp = client.post(f"/api/matrix/{matrix_id}/cancel")
        assert resp.status_code == 400

    def test_regenerate_diagonal_cell_rejected(self, client, mock_create):
        create_resp = client.post("/api/matrix/", json={"theme": "Test", "n": 2})
        matrix_id = create_resp.json()["matrix"]["id"]

        # row == col → must be rejected
        resp = client.post(
            f"/api/matrix/{matrix_id}/cells/0/0/regenerate",
            json={},
        )
        assert resp.status_code == 400

    def test_get_settings(self, client):
        resp = client.get("/api/matrix-settings/")
        assert resp.status_code == 200
        s = resp.json()["settings"]
        assert s["max_concurrency"] == 4
        assert s["max_retries"] == 3
        assert s["text_model"] == "gemini-2.5-flash"

    def test_update_settings(self, client):
        new_settings = {
            "text_model": "gemini-2.5-flash",
            "image_model": "gemini-2.5-flash-image",
            "diagonal_temperature": 0.9,
            "axes_temperature": 0.8,
            "cell_temperature": 0.7,
            "validation_temperature": 0.3,
            "max_concurrency": 8,
            "max_retries": 2,
        }
        resp = client.put("/api/matrix-settings/", json={"settings": new_settings})
        assert resp.status_code == 200
        assert resp.json()["settings"]["max_concurrency"] == 8
        assert resp.json()["settings"]["max_retries"] == 2

    def test_reset_settings(self, client):
        # First modify
        modified = {
            "text_model": "gemini-2.5-flash",
            "image_model": "gemini-2.5-flash-image",
            "diagonal_temperature": 0.9,
            "axes_temperature": 0.8,
            "cell_temperature": 0.7,
            "validation_temperature": 0.3,
            "max_concurrency": 12,
            "max_retries": 1,
        }
        client.put("/api/matrix-settings/", json={"settings": modified})

        # Then reset
        resp = client.post("/api/matrix-settings/reset")
        assert resp.status_code == 200
        s = resp.json()["settings"]
        assert s["max_concurrency"] == 4
        assert s["max_retries"] == 3
