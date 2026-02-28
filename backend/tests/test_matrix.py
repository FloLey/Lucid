"""Tests for the Concept Matrix Generator — models, DB, settings, and routes."""

from __future__ import annotations

import asyncio
import pytest
from datetime import datetime
from pathlib import Path
from pydantic import ValidationError
from unittest.mock import AsyncMock, patch

from app.dependencies import container
from app.models.matrix import (
    CreateMatrixRequest,
    MatrixCell,
    MatrixProject,
    MatrixProjectCard,
    MatrixSettings,
    RegenerateCellRequest,
)
from app.services.async_utils import bounded_gather
from app.services.matrix_service import _build_grid
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


# ── 2. Literal status validation ──────────────────────────────────────────


class TestMatrixStatusLiteral:
    """Pydantic enforces Literal status values — invalid ones must be rejected."""

    _NOW = datetime(2025, 1, 1)

    def test_cell_status_rejects_invalid_value(self):
        with pytest.raises(ValidationError):
            MatrixCell(id="x", project_id="p", row=0, col=0, cell_status="broken")

    def test_cell_status_accepts_all_valid_values(self):
        for status in ("pending", "generating", "complete", "failed"):
            cell = MatrixCell(id="x", project_id="p", row=0, col=0, cell_status=status)
            assert cell.cell_status == status

    def test_project_status_rejects_invalid_value(self):
        with pytest.raises(ValidationError):
            MatrixProject(
                id="x", name="n", theme="t", n=3, status="running",
                created_at=self._NOW, updated_at=self._NOW,
            )

    def test_project_status_accepts_all_valid_values(self):
        for status in ("pending", "generating", "complete", "failed"):
            p = MatrixProject(
                id="x", name="n", theme="t", n=3, status=status,
                created_at=self._NOW, updated_at=self._NOW,
            )
            assert p.status == status

    def test_project_card_status_rejects_invalid_value(self):
        with pytest.raises(ValidationError):
            MatrixProjectCard(
                id="x", name="n", theme="t", n=3, status="unknown",
                include_images=False, created_at=self._NOW, updated_at=self._NOW,
            )

    def test_project_card_status_accepts_all_valid_values(self):
        for status in ("pending", "generating", "complete", "failed"):
            card = MatrixProjectCard(
                id="x", name="n", theme="t", n=3, status=status,
                include_images=False, created_at=self._NOW, updated_at=self._NOW,
            )
            assert card.status == status


# ── 3. Used-labels lock ────────────────────────────────────────────────────


class TestUsedLabelsLock:
    """The asyncio.Lock in _gen_one_cell ensures label appends are serialised
    so used_labels never contains duplicate entries after concurrent generation."""

    def test_labels_accumulate_without_duplicates(self):
        """Simulate the lock pattern: concurrent coroutines each append a unique
        result, and the final list must contain every label exactly once."""

        async def _run():
            diagonal_labels = ["Alpha", "Beta", "Gamma"]
            used_labels: list[str] = list(diagonal_labels)
            labels_lock = asyncio.Lock()
            appended: list[str] = []

            async def _gen_one(concept: str) -> None:
                async with labels_lock:
                    snapshot = list(used_labels)  # noqa: F841 — mirrors production code
                # Simulate slow network call; yields to event loop
                await asyncio.sleep(0)
                async with labels_lock:
                    used_labels.append(concept)
                    appended.append(concept)

            off_diagonal = [f"cell_{i}" for i in range(6)]
            await bounded_gather(
                [_gen_one(c) for c in off_diagonal],
                limit=4,
            )
            return used_labels

        result = run_async(_run())
        # All 3 diagonal + 6 off-diagonal labels must be present
        assert len(result) == 9
        # No duplicates from concurrent appends
        assert len(set(result)) == 9

    def test_snapshot_is_independent_copy(self):
        """Snapshot taken inside the lock must not be affected by later appends."""

        async def _run():
            used_labels = ["X"]
            labels_lock = asyncio.Lock()
            snapshots: list[list[str]] = []

            async def _capture():
                async with labels_lock:
                    snapshots.append(list(used_labels))
                await asyncio.sleep(0)
                async with labels_lock:
                    used_labels.append(f"new_{len(used_labels)}")

            await asyncio.gather(_capture(), _capture())
            return snapshots, used_labels

        snapshots, final = run_async(_run())
        # Final list has the original + 2 appends
        assert len(final) == 3
        # Each snapshot is a copy — mutating used_labels after doesn't change it
        for snap in snapshots:
            assert isinstance(snap, list)
            assert snap is not final


# ── 4. MatrixDB ───────────────────────────────────────────────────────────


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


# ── 5. MatrixService ──────────────────────────────────────────────────────


class TestMatrixService:
    """Tests for MatrixService project lifecycle — real DB, patched pipeline.

    These tests exercise the REAL create_and_start / cancel_generation /
    subscribe methods (not the mock_create fixture, which bypasses them).
    The background _run_pipeline is patched to avoid network calls and the
    2-second asyncio.sleep in its finally block.
    """

    def setup_method(self):
        _clear()

    @staticmethod
    def _patch_pipeline(monkeypatch, pipeline_fn=None):
        """Replace _run_pipeline with a fast no-op (or a custom fn)."""
        if pipeline_fn is None:
            async def _noop(project_id, req):
                pass
            pipeline_fn = _noop
        monkeypatch.setattr(container.matrix_service, "_run_pipeline", pipeline_fn)

    # ── create_and_start ──────────────────────────────────────────────────

    def test_create_and_start_returns_generating_status(self, monkeypatch):
        """Regression: create_and_start must return status='generating', not 'pending'.

        Before the fix, create_project returned a stale object with status='pending'
        after update_project_status had already set it to 'generating' in the DB.
        The frontend only auto-starts the SSE stream when status=='generating', so
        the stream never connected and the user saw no progress or error feedback.
        """
        self._patch_pipeline(monkeypatch)
        req = CreateMatrixRequest(theme="AI Ethics", n=2)
        project = run_async(container.matrix_service.create_and_start(req))
        assert project.status == "generating"

    def test_create_and_start_db_has_generating_status(self, monkeypatch):
        """DB must also show 'generating' immediately after create_and_start."""
        self._patch_pipeline(monkeypatch)
        req = CreateMatrixRequest(theme="AI Ethics", n=2)
        project = run_async(container.matrix_service.create_and_start(req))
        refreshed = run_async(matrix_db.get_project(project.id))
        assert refreshed.status == "generating"

    def test_create_and_start_returns_correct_fields(self, monkeypatch):
        """Returned project must carry the fields from the creation request."""
        self._patch_pipeline(monkeypatch)
        req = CreateMatrixRequest(theme="Philosophy of Mind", n=3, language="French")
        project = run_async(container.matrix_service.create_and_start(req))
        assert project.theme == "Philosophy of Mind"
        assert project.n == 3
        assert project.language == "French"
        assert len(project.cells) == 9  # 3×3 stubs created

    # ── is_generating ─────────────────────────────────────────────────────

    def test_is_generating_true_while_pipeline_active(self, monkeypatch):
        """is_generating returns True while the background task is running."""

        async def _run():
            pause = asyncio.Event()

            async def _blocking(project_id, req):
                await pause.wait()

            monkeypatch.setattr(
                container.matrix_service, "_run_pipeline", _blocking
            )
            req = CreateMatrixRequest(theme="AI Ethics", n=2)
            project = await container.matrix_service.create_and_start(req)
            await asyncio.sleep(0)  # Yield so the task can be scheduled
            is_gen = container.matrix_service.is_generating(project.id)
            pause.set()  # Unblock task so cleanup is fast
            return is_gen

        assert run_async(_run()) is True

    # ── cancel_generation ─────────────────────────────────────────────────

    def test_cancel_generation_sets_failed_status(self, monkeypatch):
        """cancel_generation marks the project 'failed' with 'Cancelled by user'."""

        async def _run():
            async def _blocking(project_id, req):
                await asyncio.sleep(999)

            monkeypatch.setattr(
                container.matrix_service, "_run_pipeline", _blocking
            )
            req = CreateMatrixRequest(theme="AI Ethics", n=2)
            project = await container.matrix_service.create_and_start(req)
            await asyncio.sleep(0)  # Let the task start
            await container.matrix_service.cancel_generation(project.id)
            return project.id

        project_id = run_async(_run())
        refreshed = run_async(matrix_db.get_project(project_id))
        assert refreshed.status == "failed"
        assert refreshed.error_message == "Cancelled by user"

    def test_cancel_generation_removes_task(self, monkeypatch):
        """After cancel_generation, is_generating returns False."""

        async def _run():
            async def _blocking(project_id, req):
                await asyncio.sleep(999)

            monkeypatch.setattr(
                container.matrix_service, "_run_pipeline", _blocking
            )
            req = CreateMatrixRequest(theme="AI Ethics", n=2)
            project = await container.matrix_service.create_and_start(req)
            await asyncio.sleep(0)
            await container.matrix_service.cancel_generation(project.id)
            return container.matrix_service.is_generating(project.id)

        assert run_async(_run()) is False

    # ── subscribe (late-subscriber path) ──────────────────────────────────

    def test_subscribe_complete_project_yields_snapshot_then_done(self):
        """Late subscriber on a complete project gets [snapshot, done] and exits."""
        p = run_async(
            matrix_db.create_project(
                theme="Test", n=2, language="English",
                style_mode="neutral", include_images=False,
            )
        )
        run_async(matrix_db.update_project_status(p.id, "complete"))

        async def _collect():
            return [e async for e in container.matrix_service.subscribe(p.id)]

        events = run_async(_collect())
        types = [e["type"] for e in events]
        assert types == ["snapshot", "done"]

    def test_subscribe_failed_project_yields_snapshot_then_error(self):
        """Late subscriber on a failed project gets [snapshot, error] and exits."""
        p = run_async(
            matrix_db.create_project(
                theme="Test", n=2, language="English",
                style_mode="neutral", include_images=False,
            )
        )
        run_async(matrix_db.update_project_status(p.id, "failed", "LLM error"))

        async def _collect():
            return [e async for e in container.matrix_service.subscribe(p.id)]

        events = run_async(_collect())
        types = [e["type"] for e in events]
        assert types == ["snapshot", "error"]

    def test_subscribe_nonexistent_project_yields_single_error(self):
        """Subscribing to a missing project yields exactly one error event."""

        async def _collect():
            return [e async for e in container.matrix_service.subscribe("no-such-id")]

        events = run_async(_collect())
        assert len(events) == 1
        assert events[0]["type"] == "error"
        assert "Not found" in events[0]["message"]

    def test_subscribe_snapshot_contains_matrix_data(self):
        """The snapshot event embeds the full matrix (id, theme, cells)."""
        p = run_async(
            matrix_db.create_project(
                theme="Snapshot Test", n=2, language="English",
                style_mode="neutral", include_images=False,
            )
        )
        run_async(matrix_db.update_project_status(p.id, "complete"))

        async def _collect():
            return [e async for e in container.matrix_service.subscribe(p.id)]

        events = run_async(_collect())
        snapshot = next(e for e in events if e["type"] == "snapshot")
        assert snapshot["matrix"]["id"] == p.id
        assert snapshot["matrix"]["theme"] == "Snapshot Test"
        assert len(snapshot["matrix"]["cells"]) == 4  # 2×2


# ── 6. _build_grid helper ─────────────────────────────────────────────────


class TestBuildGrid:
    """Unit tests for the module-level _build_grid helper in matrix_service."""

    def test_correct_shape(self):
        cells = [
            MatrixCell(id=f"c{r}{c}", project_id="p", row=r, col=c)
            for r in range(3)
            for c in range(3)
        ]
        grid = _build_grid(cells, 3)
        assert len(grid) == 3
        assert all(len(row) == 3 for row in grid)

    def test_off_diagonal_uses_concept_and_explanation(self):
        cell = MatrixCell(
            id="c01", project_id="p", row=0, col=1,
            concept="Synergy", explanation="They reinforce each other",
        )
        grid = _build_grid([cell], 2)
        assert grid[0][1]["concept"] == "Synergy"
        assert grid[0][1]["explanation"] == "They reinforce each other"

    def test_diagonal_falls_back_to_label_and_definition(self):
        """Diagonal cells have label/definition instead of concept/explanation."""
        cell = MatrixCell(
            id="c00", project_id="p", row=0, col=0,
            label="Alpha", definition="The first element",
        )
        grid = _build_grid([cell], 2)
        assert grid[0][0]["concept"] == "Alpha"
        assert grid[0][0]["explanation"] == "The first element"

    def test_concept_takes_priority_over_label(self):
        """If both concept and label are set, concept wins."""
        cell = MatrixCell(
            id="c00", project_id="p", row=0, col=0,
            concept="Concept Value", label="Label Value",
        )
        grid = _build_grid([cell], 2)
        assert grid[0][0]["concept"] == "Concept Value"

    def test_missing_positions_yield_empty_dicts(self):
        """Positions with no matching cell produce empty dicts."""
        grid = _build_grid([], 2)
        for r in range(2):
            for c in range(2):
                assert grid[r][c] == {}

    def test_out_of_bounds_cells_are_ignored(self):
        """Cells with row/col outside [0, n) are silently skipped."""
        cell = MatrixCell(id="cx", project_id="p", row=5, col=5, concept="OOB")
        grid = _build_grid([cell], 2)
        for r in range(2):
            for c in range(2):
                assert grid[r][c] == {}
