"""Unit tests for app/services/matrix_settings_manager.py."""

import json
import pytest
from pathlib import Path

from app.models.matrix import MatrixSettings
from app.services.matrix_settings_manager import MatrixSettingsManager


class TestMatrixSettingsManager:
    def test_get_returns_defaults_when_no_file(self, tmp_path):
        manager = MatrixSettingsManager(settings_file=tmp_path / "settings.json")
        settings = manager.get()
        assert isinstance(settings, MatrixSettings)
        assert settings == MatrixSettings()

    def test_update_persists_to_file(self, tmp_path):
        path = tmp_path / "settings.json"
        manager = MatrixSettingsManager(settings_file=path)

        updated = MatrixSettings(max_concurrency=8, max_retries=5)
        manager.update(updated)

        assert path.exists()
        data = json.loads(path.read_text())
        assert data["max_concurrency"] == 8
        assert data["max_retries"] == 5

    def test_get_reflects_updated_value(self, tmp_path):
        manager = MatrixSettingsManager(settings_file=tmp_path / "settings.json")
        manager.update(MatrixSettings(max_concurrency=8))
        assert manager.get().max_concurrency == 8

    def test_reset_reverts_to_defaults(self, tmp_path):
        manager = MatrixSettingsManager(settings_file=tmp_path / "settings.json")
        manager.update(MatrixSettings(max_concurrency=8))
        manager.reset()
        assert manager.get().max_concurrency == MatrixSettings().max_concurrency

    def test_reset_overwrites_file_with_defaults(self, tmp_path):
        path = tmp_path / "settings.json"
        manager = MatrixSettingsManager(settings_file=path)
        manager.update(MatrixSettings(max_concurrency=8))
        manager.reset()
        data = json.loads(path.read_text())
        assert data["max_concurrency"] == MatrixSettings().max_concurrency

    def test_load_reads_existing_file(self, tmp_path):
        path = tmp_path / "settings.json"
        path.write_text(json.dumps({"max_concurrency": 12, "max_retries": 2}))
        manager = MatrixSettingsManager(settings_file=path)
        assert manager.get().max_concurrency == 12
        assert manager.get().max_retries == 2

    def test_load_falls_back_to_defaults_on_corrupt_json(self, tmp_path):
        path = tmp_path / "settings.json"
        path.write_text("this is not valid json {{{{")
        manager = MatrixSettingsManager(settings_file=path)
        assert manager.get() == MatrixSettings()

    def test_update_raises_on_unwritable_path(self, tmp_path):
        # Point settings file at a path whose parent directory doesn't exist
        path = tmp_path / "nonexistent_dir" / "settings.json"
        manager = MatrixSettingsManager(settings_file=path)
        with pytest.raises(Exception):
            manager.update(MatrixSettings())

    def test_round_trip_preserves_all_fields(self, tmp_path):
        path = tmp_path / "settings.json"
        original = MatrixSettings(
            max_concurrency=6,
            max_retries=2,
            diagonal_temperature=0.5,
        )
        manager = MatrixSettingsManager(settings_file=path)
        manager.update(original)

        # Create a fresh manager to force a re-load from disk
        manager2 = MatrixSettingsManager(settings_file=path)
        loaded = manager2.get()
        assert loaded.max_concurrency == 6
        assert loaded.max_retries == 2
        assert loaded.diagonal_temperature == pytest.approx(0.5)
