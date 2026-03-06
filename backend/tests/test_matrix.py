"""Tests for the Concept Matrix Generator — models, DB, settings, and routes."""

from __future__ import annotations

import asyncio
import pytest
from datetime import datetime
from pathlib import Path
from pydantic import ValidationError
from unittest.mock import AsyncMock, MagicMock, patch

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
from app.services.gemini_service import GeminiError, GeminiService
from app.services.matrix_generator import MatrixGenerator
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

    # ── Description mode validation ───────────────────────────────────────

    def test_create_request_description_mode_valid(self):
        req = CreateMatrixRequest(
            input_mode="description",
            description="feels like a certain generation but is actually from one",
            n=3,
        )
        assert req.input_mode == "description"
        assert "generation" in req.description
        assert req.n == 3
        assert req.theme == ""  # theme is blank in description mode

    def test_create_request_description_mode_defaults(self):
        req = CreateMatrixRequest(
            input_mode="description",
            description="enjoyed by X but intended for Y",
        )
        assert req.n == 4
        assert req.language == "English"
        assert req.style_mode == "neutral"
        assert req.include_images is False

    def test_create_request_description_mode_missing_description_raises(self):
        with pytest.raises(ValidationError):
            CreateMatrixRequest(input_mode="description")

    def test_create_request_description_mode_empty_description_raises(self):
        with pytest.raises(ValidationError):
            CreateMatrixRequest(input_mode="description", description="   ")

    def test_create_request_theme_mode_empty_theme_raises(self):
        with pytest.raises(ValidationError):
            CreateMatrixRequest(input_mode="theme", theme="")

    def test_create_request_theme_mode_short_theme_raises(self):
        with pytest.raises(ValidationError):
            CreateMatrixRequest(input_mode="theme", theme="ab")

    def test_create_request_theme_mode_still_works(self):
        req = CreateMatrixRequest(theme="Cooking Techniques", n=4)
        assert req.input_mode == "theme"
        assert req.theme == "Cooking Techniques"
        assert req.description is None

    def test_create_request_description_mode_non_square(self):
        """n_rows and n_cols can differ in description mode."""
        req = CreateMatrixRequest(
            input_mode="description",
            description="feels like X but is actually Y",
            n_rows=3,
            n_cols=5,
        )
        assert req.effective_n_rows == 3
        assert req.effective_n_cols == 5

    def test_create_request_description_mode_n_rows_too_large(self):
        """n_rows > 8 must be rejected."""
        with pytest.raises(ValidationError):
            CreateMatrixRequest(
                input_mode="description",
                description="feels like X but is actually Y",
                n_rows=9,
            )

    def test_create_request_description_mode_n_cols_too_large(self):
        """n_cols > 8 must be rejected."""
        with pytest.raises(ValidationError):
            CreateMatrixRequest(
                input_mode="description",
                description="feels like X but is actually Y",
                n_cols=9,
            )

    def test_create_request_description_mode_defaults_n_rows_n_cols(self):
        """Without explicit n_rows/n_cols, effective values fall back to n."""
        req = CreateMatrixRequest(
            input_mode="description",
            description="feels like X but is actually Y",
            n=4,
        )
        assert req.effective_n_rows == 4
        assert req.effective_n_cols == 4

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

    def test_create_project_description_mode_stores_fields(self):
        _clear()
        project = run_async(
            matrix_db.create_project(
                theme="feels like X but is actually Y",
                n=3,
                language="English",
                style_mode="neutral",
                include_images=False,
                input_mode="description",
                description="feels like a certain generation but is actually from one",
            )
        )
        assert project.input_mode == "description"
        assert project.description == "feels like a certain generation but is actually from one"
        assert project.theme == "feels like X but is actually Y"

    def test_create_project_theme_mode_has_default_input_mode(self):
        _clear()
        project = run_async(
            matrix_db.create_project(
                theme="AI Ethics",
                n=3,
                language="English",
                style_mode="neutral",
                include_images=False,
            )
        )
        assert project.input_mode == "theme"
        assert project.description is None

    def test_create_project_non_square_stubs(self):
        """Description mode with n_rows=3, n_cols=5 creates 15 cell stubs."""
        _clear()
        project = run_async(
            matrix_db.create_project(
                theme="desc",
                n=4,
                language="English",
                style_mode="neutral",
                include_images=False,
                input_mode="description",
                description="enjoyed by X but intended for Y",
                n_rows=3,
                n_cols=5,
            )
        )
        assert project.n_rows == 3
        assert project.n_cols == 5
        assert len(project.cells) == 15  # 3×5

    def test_create_project_non_square_all_positions_exist(self):
        """Every (row, col) position in a 3×5 matrix must have a cell stub."""
        _clear()
        project = run_async(
            matrix_db.create_project(
                theme="desc",
                n=4,
                language="English",
                style_mode="neutral",
                include_images=False,
                input_mode="description",
                description="enjoyed by X but intended for Y",
                n_rows=3,
                n_cols=5,
            )
        )
        positions = {(c.row, c.col) for c in project.cells}
        expected = {(r, c) for r in range(3) for c in range(5)}
        assert positions == expected

    def test_update_project_labels_round_trips(self):
        """update_project_labels persists row_labels/col_labels to DB."""
        _clear()
        project = run_async(
            matrix_db.create_project(
                theme="desc",
                n=3,
                language="English",
                style_mode="neutral",
                include_images=False,
                input_mode="description",
                description="enjoyed by X but intended for Y",
                n_rows=3,
                n_cols=3,
            )
        )
        run_async(matrix_db.update_project_labels(
            project.id,
            row_labels=["Row A", "Row B", "Row C"],
            col_labels=["Col 1", "Col 2", "Col 3"],
        ))
        refreshed = run_async(matrix_db.get_project(project.id))
        assert refreshed.row_labels == ["Row A", "Row B", "Row C"]
        assert refreshed.col_labels == ["Col 1", "Col 2", "Col 3"]


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
        effective_theme = (
            req.description if req.input_mode == "description" else req.theme
        )
        p = await matrix_db.create_project(
            theme=effective_theme or "",
            n=req.n,
            language=req.language,
            style_mode=req.style_mode,
            include_images=req.include_images,
            name=req.name,
            input_mode=req.input_mode,
            description=req.description,
            n_rows=req.effective_n_rows if req.input_mode == "description" else 0,
            n_cols=req.effective_n_cols if req.input_mode == "description" else 0,
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

    def test_create_matrix_description_mode(self, client, mock_create):
        payload = {
            "input_mode": "description",
            "description": "feels like a certain generation but is actually from one",
            "n": 3,
        }
        resp = client.post("/api/matrix/", json=payload)
        assert resp.status_code == 200
        data = resp.json()["matrix"]
        assert data["input_mode"] == "description"
        assert data["description"] == "feels like a certain generation but is actually from one"
        assert data["n"] == 3
        assert data["status"] == "generating"

    def test_create_matrix_description_mode_non_square(self, client, mock_create):
        """Route accepts n_rows/n_cols and returns correct dimensions."""
        payload = {
            "input_mode": "description",
            "description": "enjoyed by X but intended for Y",
            "n_rows": 3,
            "n_cols": 5,
        }
        resp = client.post("/api/matrix/", json=payload)
        assert resp.status_code == 200
        data = resp.json()["matrix"]
        assert data["input_mode"] == "description"
        assert data["n_rows"] == 3
        assert data["n_cols"] == 5
        # 3×5 = 15 cell stubs
        assert len(data["cells"]) == 15

    def test_create_matrix_description_mode_n_rows_too_large(self, client, mock_create):
        """n_rows > 8 must be rejected with 422."""
        resp = client.post("/api/matrix/", json={
            "input_mode": "description",
            "description": "enjoyed by X but intended for Y",
            "n_rows": 9,
        })
        assert resp.status_code == 422

    def test_create_matrix_description_mode_missing_description_returns_422(self, client, mock_create):
        resp = client.post("/api/matrix/", json={"input_mode": "description"})
        assert resp.status_code == 422

    def test_create_matrix_description_mode_empty_description_returns_422(self, client, mock_create):
        resp = client.post("/api/matrix/", json={"input_mode": "description", "description": "  "})
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

    def test_generate_images_not_found(self, client):
        resp = client.post("/api/matrix/nonexistent-id/generate-images")
        assert resp.status_code == 404

    def test_generate_images_starts_background_task(self, client, mock_create, monkeypatch):
        # Create a complete matrix without images
        create_resp = client.post("/api/matrix/", json={"theme": "Climate Change", "n": 2})
        matrix_id = create_resp.json()["matrix"]["id"]
        run_async(matrix_db.update_project_status(matrix_id, "complete"))

        generated = []

        async def _fake_generate(project_id: str):
            generated.append(project_id)

        monkeypatch.setattr(container.matrix_service, "generate_images_for_project", _fake_generate)
        monkeypatch.setattr(container.matrix_service, "is_generating", lambda pid: False)

        resp = client.post(f"/api/matrix/{matrix_id}/generate-images")
        assert resp.status_code == 200
        assert resp.json() == {"started": True}

    def test_generate_images_rejected_when_already_generating(self, client, mock_create, monkeypatch):
        create_resp = client.post("/api/matrix/", json={"theme": "Philosophy", "n": 2})
        matrix_id = create_resp.json()["matrix"]["id"]

        monkeypatch.setattr(container.matrix_service, "is_generating", lambda pid: True)

        resp = client.post(f"/api/matrix/{matrix_id}/generate-images")
        assert resp.status_code == 400
        assert "already in progress" in resp.json()["detail"]


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

    def test_subscribe_failed_project_error_event_includes_message(self):
        """The error SSE event for a late subscriber must include the stored error_message."""
        p = run_async(
            matrix_db.create_project(
                theme="Test", n=2, language="English",
                style_mode="neutral", include_images=False,
            )
        )
        run_async(matrix_db.update_project_status(p.id, "failed", "Diagonal generation failed"))

        async def _collect():
            return [e async for e in container.matrix_service.subscribe(p.id)]

        events = run_async(_collect())
        error_event = next(e for e in events if e["type"] == "error")
        assert "message" in error_event
        assert error_event["message"] == "Diagonal generation failed"

    def test_subscribe_failed_project_error_event_fallback_when_no_message(self):
        """When error_message is None on a failed project, the error event still has a non-empty message."""
        p = run_async(
            matrix_db.create_project(
                theme="Test", n=2, language="English",
                style_mode="neutral", include_images=False,
            )
        )
        run_async(matrix_db.update_project_status(p.id, "failed"))

        async def _collect():
            return [e async for e in container.matrix_service.subscribe(p.id)]

        events = run_async(_collect())
        error_event = next(e for e in events if e["type"] == "error")
        assert "message" in error_event
        assert error_event["message"]  # non-empty fallback

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
        grid = _build_grid(cells, 3, 3)
        assert len(grid) == 3
        assert all(len(row) == 3 for row in grid)

    def test_off_diagonal_uses_concept_and_explanation(self):
        cell = MatrixCell(
            id="c01", project_id="p", row=0, col=1,
            concept="Synergy", explanation="They reinforce each other",
        )
        grid = _build_grid([cell], 2, 2)
        assert grid[0][1]["concept"] == "Synergy"
        assert grid[0][1]["explanation"] == "They reinforce each other"

    def test_diagonal_falls_back_to_label_and_definition(self):
        """Diagonal cells have label/definition instead of concept/explanation."""
        cell = MatrixCell(
            id="c00", project_id="p", row=0, col=0,
            label="Alpha", definition="The first element",
        )
        grid = _build_grid([cell], 2, 2)
        assert grid[0][0]["concept"] == "Alpha"
        assert grid[0][0]["explanation"] == "The first element"

    def test_concept_takes_priority_over_label(self):
        """If both concept and label are set, concept wins."""
        cell = MatrixCell(
            id="c00", project_id="p", row=0, col=0,
            concept="Concept Value", label="Label Value",
        )
        grid = _build_grid([cell], 2, 2)
        assert grid[0][0]["concept"] == "Concept Value"

    def test_missing_positions_yield_empty_dicts(self):
        """Positions with no matching cell produce empty dicts."""
        grid = _build_grid([], 2, 2)
        for r in range(2):
            for c in range(2):
                assert grid[r][c] == {}

    def test_out_of_bounds_cells_are_ignored(self):
        """Cells with row/col outside [0, n) are silently skipped."""
        cell = MatrixCell(id="cx", project_id="p", row=5, col=5, concept="OOB")
        grid = _build_grid([cell], 2, 2)
        for r in range(2):
            for c in range(2):
                assert grid[r][c] == {}

    def test_rectangular_grid_shape(self):
        """Non-square: 3 rows × 5 cols produces the right dimensions."""
        cells = [
            MatrixCell(id=f"c{r}{c}", project_id="p", row=r, col=c, concept=f"{r},{c}")
            for r in range(3)
            for c in range(5)
        ]
        grid = _build_grid(cells, 3, 5)
        assert len(grid) == 3
        assert all(len(row) == 5 for row in grid)
        assert grid[2][4]["concept"] == "2,4"


# ── 7. Prompt template formatting ─────────────────────────────────────────


class TestMatrixPromptFormatting:
    """Verify that every matrix prompt template can be formatted with its
    expected keyword arguments without raising a KeyError.

    Prompt files contain JSON examples with curly braces.  If those braces are
    not escaped (``{{`` / ``}}``) Python's str.format() treats them as
    placeholder fields, producing a KeyError that surfaces in the frontend as
    the raw key name (e.g. ``'"concepts"'``).
    """

    @pytest.fixture
    def loader(self):
        from app.services.prompt_loader import PromptLoader
        return PromptLoader()

    @pytest.mark.parametrize("name,kwargs,sentinel", [
        (
            "matrix_diagonal",
            {"theme": "Cooking Techniques", "n": 4, "language": "English", "style_mode": "neutral"},
            "Cooking Techniques",
        ),
        (
            "matrix_axes",
            {
                "index": 0,
                "concept_label": "Fermentation",
                "concept_definition": "Microbial transformation of ingredients.",
                "all_concepts_json": '["Fermentation", "Emulsification"]',
            },
            "Fermentation",
        ),
        (
            "matrix_cell",
            {
                "theme": "Cooking Techniques",
                "style_mode": "neutral",
                "row_label": "Fermentation",
                "col_label": "Emulsification",
                "row_descriptor": "microbial transformation quality",
                "col_descriptor": "fat-water binding quality",
                "already_used_labels": "none",
                "extra_instructions": "",
            },
            "Fermentation",
        ),
        (
            "matrix_validator",
            {"theme": "Cooking Techniques", "matrix_json": '[{"row": 0, "col": 1, "concept": "Kimchi"}]'},
            "Cooking Techniques",
        ),
        (
            "matrix_description_axes",
            {
                "description": "feels like a certain generation but is actually from one",
                "n_rows": 4,
                "n_cols": 4,
                "language": "English",
                "style_mode": "neutral",
            },
            "feels like a certain generation",
        ),
    ])
    def test_prompt_formats_without_error(self, loader, name, kwargs, sentinel):
        """Each prompt must format cleanly and include a known sentinel value."""
        template = loader.get_cached(name)
        assert template, f"{name} prompt must not be empty"
        result = template.format(**kwargs)
        assert sentinel in result

    @pytest.mark.parametrize("name,kwargs,expected_keys", [
        (
            "matrix_diagonal",
            {"theme": "T", "n": 3, "language": "English", "style_mode": "fun"},
            ['"concepts"'],
        ),
        (
            "matrix_axes",
            {"index": 1, "concept_label": "X", "concept_definition": "Y", "all_concepts_json": "[]"},
            ['"row_descriptor"', '"col_descriptor"'],
        ),
        (
            "matrix_description_axes",
            {
                "description": "enjoys X but was made for Y",
                "n_rows": 3,
                "n_cols": 4,
                "language": "English",
                "style_mode": "neutral",
            },
            ['"row_axis_label"', '"col_axis_label"', '"row_labels"', '"col_labels"'],
        ),
    ])
    def test_prompt_output_contains_literal_json_keys(self, loader, name, kwargs, expected_keys):
        """After formatting, JSON example keys must appear as literal strings
        (not silently consumed as format fields)."""
        template = loader.get_cached(name)
        result = template.format(**kwargs)
        for key in expected_keys:
            assert key in result


# ── 8. GeminiService.generate_json type validation ────────────────────────


class TestGenerateJsonTypeValidation:
    """generate_json must raise GeminiError when the LLM returns a non-dict type.

    Root cause: json.loads() can return a list, number, or string — not just a
    dict.  Any caller that does raw.get(...) on such a value crashes with:
        AttributeError: 'list' object has no attribute 'get'
    The fix validates the parsed type inside generate_json itself so every
    call site gets the protection automatically.
    """

    @pytest.fixture
    def gemini_svc(self):
        return GeminiService()

    def test_raises_gemini_error_when_response_is_list(self, gemini_svc):
        """A bare JSON array from the LLM raises GeminiError, not AttributeError."""
        with patch.object(
            gemini_svc, "generate_text", new=AsyncMock(return_value='[{"label": "A"}]')
        ):
            with pytest.raises(GeminiError, match="Expected JSON object"):
                run_async(gemini_svc.generate_json("test prompt"))

    def test_raises_gemini_error_when_response_is_number(self, gemini_svc):
        """A bare JSON number from the LLM raises GeminiError."""
        with patch.object(
            gemini_svc, "generate_text", new=AsyncMock(return_value="42")
        ):
            with pytest.raises(GeminiError, match="Expected JSON object"):
                run_async(gemini_svc.generate_json("test prompt"))

    def test_succeeds_when_response_is_dict(self, gemini_svc):
        """A proper JSON object is returned as a dict without error."""
        with patch.object(
            gemini_svc, "generate_text", new=AsyncMock(return_value='{"concepts": []}')
        ):
            result = run_async(gemini_svc.generate_json("test prompt"))
            assert result == {"concepts": []}


# ── 9. MatrixGenerator LLM response robustness ────────────────────────────


class TestMatrixGeneratorLLMRobustness:
    """MatrixGenerator methods must not raise AttributeError when the LLM
    returns a non-dict JSON value.

    After the fix in GeminiService.generate_json, such responses raise
    GeminiError instead.  Each generator method should either propagate that
    error (so MatrixService can retry) or fall back gracefully (validate_matrix).
    """

    @pytest.fixture
    def generator(self):
        """MatrixGenerator wired with fully-mocked dependencies."""
        gemini = AsyncMock()
        prompt_loader = MagicMock()
        # Return a plain string with no format fields so .format(**kwargs) is safe
        prompt_loader.get_cached.return_value = "static test prompt"
        return MatrixGenerator(
            gemini_service=gemini,
            image_service=AsyncMock(),
            storage_service=MagicMock(),
            prompt_loader=prompt_loader,
        )

    @staticmethod
    async def _noop_emit(event: dict) -> None:
        pass

    def test_generate_diagonal_propagates_gemini_error_from_list_response(self, generator):
        """generate_diagonal must raise GeminiError (not AttributeError) when
        generate_json raises because the LLM returned a list."""
        generator._gemini_service.generate_json.side_effect = GeminiError(
            "Expected JSON object from AI, got list"
        )
        settings = MatrixSettings()
        with pytest.raises(GeminiError, match="Expected JSON object"):
            run_async(
                generator.generate_diagonal(
                    project_id="test",
                    theme="AI Ethics",
                    n=3,
                    language="English",
                    style_mode="neutral",
                    settings=settings,
                    emit=self._noop_emit,
                )
            )

    def test_generate_axes_propagates_gemini_error_from_list_response(self, generator):
        """generate_axes_for_concept must raise GeminiError when generate_json does."""
        generator._gemini_service.generate_json.side_effect = GeminiError(
            "Expected JSON object from AI, got list"
        )
        settings = MatrixSettings()
        concept = {"label": "Alpha", "definition": "The first"}
        with pytest.raises(GeminiError, match="Expected JSON object"):
            run_async(
                generator.generate_axes_for_concept(
                    project_id="test",
                    diagonal_index=0,
                    concept=concept,
                    all_concepts=[concept],
                    settings=settings,
                    emit=self._noop_emit,
                )
            )

    def test_generate_cell_propagates_gemini_error_from_list_response(self, generator):
        """generate_cell must raise GeminiError when generate_json does."""
        generator._gemini_service.generate_json.side_effect = GeminiError(
            "Expected JSON object from AI, got list"
        )
        settings = MatrixSettings()
        row_c = {"label": "Alpha", "definition": "The first"}
        col_c = {"label": "Beta", "definition": "The second"}
        with pytest.raises(GeminiError, match="Expected JSON object"):
            run_async(
                generator.generate_cell(
                    project_id="test",
                    row=0,
                    col=1,
                    row_concept=row_c,
                    col_concept=col_c,
                    row_descriptor="quality A",
                    col_descriptor="quality B",
                    already_used_labels=[],
                    theme="AI Ethics",
                    style_mode="neutral",
                    settings=settings,
                    emit=self._noop_emit,
                )
            )

    def test_validate_matrix_falls_back_to_empty_on_list_response(self, generator):
        """validate_matrix catches GeminiError and treats all cells as valid,
        returning an empty failures list."""
        generator._gemini_service.generate_json.side_effect = GeminiError(
            "Expected JSON object from AI, got list"
        )
        settings = MatrixSettings()
        cells_grid = [
            [{"concept": "A", "explanation": "a"}, {"concept": "B", "explanation": "b"}],
            [{"concept": "C", "explanation": "c"}, {"concept": "D", "explanation": "d"}],
        ]
        axes = [("row_desc_0", "col_desc_0"), ("row_desc_1", "col_desc_1")]
        failures = run_async(
            generator.validate_matrix(
                project_id="test",
                theme="AI Ethics",
                cells_grid=cells_grid,
                axes=axes,
                settings=settings,
                emit=self._noop_emit,
            )
        )
        assert failures == []


# ── 9. generate_from_description ─────────────────────────────────────────


class TestGenerateFromDescription:
    """Unit tests for MatrixGenerator.generate_from_description."""

    @pytest.fixture
    def generator(self):
        gemini = AsyncMock()
        prompt_loader = MagicMock()
        prompt_loader.get_cached.return_value = "static test prompt"
        return MatrixGenerator(
            gemini_service=gemini,
            image_service=AsyncMock(),
            storage_service=MagicMock(),
            prompt_loader=prompt_loader,
        )

    @staticmethod
    async def _collect_emit(event: dict, events: list) -> None:
        events.append(event)

    def test_returns_correct_concepts_and_axes(self, generator):
        generator._gemini_service.generate_json.return_value = {
            "row_axis_label": "Is actually",
            "col_axis_label": "Feels like",
            "row_labels": ["Gen-Z", "Millennial", "Gen-X"],
            "row_definitions": ["Born 1997-2012", "Born 1981-1996", "Born 1965-1980"],
            "col_labels": ["Gen-Z", "Millennial", "Gen-X"],
            "col_definitions": ["Born 1997-2012", "Born 1981-1996", "Born 1965-1980"],
        }
        settings = MatrixSettings()
        events: list = []
        row_concepts, col_concepts, row_axes, col_axes = run_async(
            generator.generate_from_description(
                project_id="test",
                description="feels like a generation but is actually from one",
                n_rows=3,
                n_cols=3,
                language="English",
                style_mode="neutral",
                settings=settings,
                emit=lambda e: self._collect_emit(e, events),
            )
        )
        assert len(row_concepts) == 3
        assert row_concepts[0] == {"label": "Gen-Z", "definition": "Born 1997-2012"}
        assert row_concepts[2] == {"label": "Gen-X", "definition": "Born 1965-1980"}

        assert len(row_axes) == 3
        assert row_axes[0] == "Is actually Gen-Z"
        assert row_axes[1] == "Is actually Millennial"
        assert col_axes[0] == "Feels like Gen-Z"

    def test_returns_independent_row_col_labels_non_square(self, generator):
        """When n_rows != n_cols, row and col labels must be independently parsed."""
        generator._gemini_service.generate_json.return_value = {
            "row_axis_label": "Was intended for",
            "col_axis_label": "Is enjoyed by",
            "row_labels": ["Children", "Seniors"],
            "row_definitions": ["Under 12", "65+"],
            "col_labels": ["Nerds", "Jocks", "Gamers"],
            "col_definitions": ["Tech fans", "Sports fans", "Gaming fans"],
        }
        settings = MatrixSettings()
        events: list = []
        row_concepts, col_concepts, row_axes, col_axes = run_async(
            generator.generate_from_description(
                project_id="test",
                description="intended for X but enjoyed by Y",
                n_rows=2,
                n_cols=3,
                language="English",
                style_mode="neutral",
                settings=settings,
                emit=lambda e: self._collect_emit(e, events),
            )
        )
        assert len(row_concepts) == 2
        assert len(col_concepts) == 3
        assert row_concepts[0]["label"] == "Children"
        assert col_concepts[2]["label"] == "Gamers"
        assert len(row_axes) == 2
        assert len(col_axes) == 3

    def test_emits_axes_events_only_no_diagonal(self, generator):
        """generate_from_description must emit axes events but NOT diagonal events.

        In description mode all cells (including diagonal) are generated equally
        via the cell generation step, so no cells should be pre-populated here.
        """
        generator._gemini_service.generate_json.return_value = {
            "row_axis_label": "Was intended for",
            "col_axis_label": "Is enjoyed by",
            "row_labels": ["Nerds", "Jocks"],
            "row_definitions": ["Tech enthusiasts", "Sports fans"],
            "col_labels": ["Nerds", "Jocks"],
            "col_definitions": ["Tech enthusiasts", "Sports fans"],
        }
        settings = MatrixSettings()
        events: list = []
        run_async(
            generator.generate_from_description(
                project_id="proj-1",
                description="intended for X enjoyed by Y",
                n_rows=2,
                n_cols=2,
                language="English",
                style_mode="neutral",
                settings=settings,
                emit=lambda e: self._collect_emit(e, events),
            )
        )
        diagonal_events = [e for e in events if e["type"] == "diagonal"]
        axes_events = [e for e in events if e["type"] == "axes"]
        # No diagonal events — cells are not pre-populated in description mode
        assert len(diagonal_events) == 0
        # Axes events provide header descriptors for the frontend
        assert len(axes_events) == 2
        assert axes_events[0]["row_descriptor"] == "Was intended for Nerds"
        assert axes_events[0]["col_descriptor"] == "Is enjoyed by Nerds"

    def test_raises_gemini_error_when_too_few_row_labels(self, generator):
        generator._gemini_service.generate_json.return_value = {
            "row_axis_label": "Is actually",
            "col_axis_label": "Feels like",
            "row_labels": ["Gen-Z"],  # only 1, need 3
            "row_definitions": ["Born 1997-2012"],
            "col_labels": ["Gen-Z", "Millennial", "Gen-X"],
            "col_definitions": ["Born 1997-2012", "Born 1981-1996", "Born 1965-1980"],
        }
        settings = MatrixSettings()
        events: list = []
        with pytest.raises(GeminiError, match="row labels"):
            run_async(
                generator.generate_from_description(
                    project_id="test",
                    description="some description",
                    n_rows=3,
                    n_cols=3,
                    language="English",
                    style_mode="neutral",
                    settings=settings,
                    emit=lambda e: self._collect_emit(e, events),
                )
            )

    def test_raises_gemini_error_when_too_few_col_labels(self, generator):
        generator._gemini_service.generate_json.return_value = {
            "row_axis_label": "Is actually",
            "col_axis_label": "Feels like",
            "row_labels": ["Gen-Z", "Millennial", "Gen-X"],
            "row_definitions": ["Born 1997-2012", "Born 1981-1996", "Born 1965-1980"],
            "col_labels": ["Gen-Z"],  # only 1, need 3
            "col_definitions": ["Born 1997-2012"],
        }
        settings = MatrixSettings()
        events: list = []
        with pytest.raises(GeminiError, match="col labels"):
            run_async(
                generator.generate_from_description(
                    project_id="test",
                    description="some description",
                    n_rows=3,
                    n_cols=3,
                    language="English",
                    style_mode="neutral",
                    settings=settings,
                    emit=lambda e: self._collect_emit(e, events),
                )
            )

    def test_propagates_gemini_error_from_generate_json(self, generator):
        generator._gemini_service.generate_json.side_effect = GeminiError(
            "Expected JSON object from AI, got list"
        )
        settings = MatrixSettings()
        events: list = []
        with pytest.raises(GeminiError, match="Expected JSON object"):
            run_async(
                generator.generate_from_description(
                    project_id="test",
                    description="some description",
                    n_rows=3,
                    n_cols=3,
                    language="English",
                    style_mode="neutral",
                    settings=settings,
                    emit=lambda e: self._collect_emit(e, events),
                )
            )

    def test_pads_missing_definitions(self, generator):
        """If the LLM returns fewer definitions than labels, pad with empty strings."""
        generator._gemini_service.generate_json.return_value = {
            "row_axis_label": "Is actually",
            "col_axis_label": "Feels like",
            "row_labels": ["Gen-Z", "Millennial", "Gen-X"],
            "row_definitions": ["Born 1997-2012"],  # only 1 definition for 3 labels
            "col_labels": ["Gen-Z", "Millennial", "Gen-X"],
            "col_definitions": [],  # completely missing
        }
        settings = MatrixSettings()
        events: list = []
        row_concepts, col_concepts, _, _ = run_async(
            generator.generate_from_description(
                project_id="test",
                description="some description",
                n_rows=3,
                n_cols=3,
                language="English",
                style_mode="neutral",
                settings=settings,
                emit=lambda e: self._collect_emit(e, events),
            )
        )
        assert row_concepts[0]["definition"] == "Born 1997-2012"
        assert row_concepts[1]["definition"] == ""
        assert row_concepts[2]["definition"] == ""
        assert col_concepts[0]["definition"] == ""


# ── 10. Description mode pipeline: all cells generated equally ────────────


class TestDescriptionModePipeline:
    """Verify that _run_pipeline in description mode generates all n² cells,
    including diagonal cells, via the cell generation step.
    """

    def setup_method(self):
        _clear()

    def test_description_mode_generates_all_n_squared_cells(self, monkeypatch):
        """In description mode, diagonal cells must NOT be pre-populated.

        All n² positions (including diagonal) should go through generate_cell,
        so the final DB state has complete cells everywhere.
        """
        n = 2
        generated_positions: list[tuple[int, int]] = []

        async def _run():
            # Stub generate_from_description: return labels + axes, no diagonal events
            async def _fake_from_description(project_id, description, n_rows, n_cols,
                                             language, style_mode, settings, emit):
                row_concepts = [
                    {"label": "Alpha", "definition": "def-alpha"},
                    {"label": "Beta", "definition": "def-beta"},
                ]
                col_concepts = [
                    {"label": "Alpha", "definition": "def-alpha"},
                    {"label": "Beta", "definition": "def-beta"},
                ]
                row_axes = ["Row Alpha", "Row Beta"]
                col_axes = ["Col Alpha", "Col Beta"]
                # Emit only axes events (no diagonal events — mirrors new behaviour)
                for i, rd in enumerate(row_axes):
                    await emit({
                        "type": "axes", "project_id": project_id,
                        "row": i, "col": i,
                        "row_descriptor": rd, "col_descriptor": col_axes[i],
                    })
                return row_concepts, col_concepts, row_axes, col_axes

            # Stub generate_cell: record which positions were requested
            async def _fake_generate_cell(project_id, row, col, row_concept,
                                          col_concept, row_descriptor, col_descriptor,
                                          already_used_labels, theme, style_mode,
                                          settings, emit, extra_instructions=""):
                generated_positions.append((row, col))
                await emit({
                    "type": "cell", "project_id": project_id,
                    "row": row, "col": col,
                    "concept": f"Concept-{row}-{col}",
                    "explanation": f"Exp-{row}-{col}",
                })
                return {"concept": f"Concept-{row}-{col}", "explanation": f"Exp-{row}-{col}"}

            # Stub validate_matrix: no failures
            async def _fake_validate(project_id, theme, cells_grid, settings, emit, **kwargs):
                return []

            monkeypatch.setattr(container.matrix_service._gen, "generate_from_description",
                                _fake_from_description)
            monkeypatch.setattr(container.matrix_service._gen, "generate_cell",
                                _fake_generate_cell)
            monkeypatch.setattr(container.matrix_service._gen, "validate_matrix",
                                _fake_validate)

            req = CreateMatrixRequest(
                input_mode="description",
                description="feels like one era but is actually another",
                n=n,
                include_images=False,
            )
            project = await container.matrix_service.create_and_start(req)
            # Wait for background pipeline to finish (it patches sleep away)
            for _ in range(50):
                await asyncio.sleep(0.05)
                p = await matrix_db.get_project(project.id)
                if p and p.status in ("complete", "failed"):
                    break
            return project.id

        project_id = run_async(_run())

        # All 4 positions (0,0), (0,1), (1,0), (1,1) must have been generated
        assert len(generated_positions) == n * n
        expected = {(r, c) for r in range(n) for c in range(n)}
        assert set(generated_positions) == expected

        # Diagonal cells must have concept set (description mode: no label field)
        final = run_async(matrix_db.get_project(project_id))
        for r in range(n):
            diag_cell = next(c for c in final.cells if c.row == r and c.col == r)
            assert diag_cell.concept == f"Concept-{r}-{r}"
