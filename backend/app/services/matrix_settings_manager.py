"""Settings manager for matrix_settings.json."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.models.matrix import MatrixSettings

logger = logging.getLogger(__name__)

_SETTINGS_FILE = Path("matrix_settings.json")


class MatrixSettingsManager:
    """Read/write matrix_settings.json (same pattern as ConfigManager)."""

    def __init__(self, settings_file: Path = _SETTINGS_FILE) -> None:
        self._file = settings_file
        self.settings: MatrixSettings = self._load()

    def _load(self) -> MatrixSettings:
        if self._file.exists():
            try:
                with open(self._file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return MatrixSettings(**data)
            except Exception as exc:
                logger.warning(
                    "Failed to load %s (%s) — using defaults", self._file, exc
                )
        return MatrixSettings()

    def get(self) -> MatrixSettings:
        return self.settings

    def update(self, settings: MatrixSettings) -> MatrixSettings:
        self.settings = settings
        try:
            with open(self._file, "w", encoding="utf-8") as f:
                json.dump(settings.model_dump(), f, indent=2)
        except Exception as exc:
            logger.error("Failed to save %s: %s", self._file, exc)
            raise
        return self.settings

    def reset(self) -> MatrixSettings:
        return self.update(MatrixSettings())
