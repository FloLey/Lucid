"""Configuration management service for Lucid application."""

import json
import logging
from pathlib import Path
from typing import Optional

from app.models.config import AppConfig

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages application configuration with JSON persistence."""

    def __init__(self, config_file: str = "config.json"):
        """Initialize config manager and load configuration.

        Args:
            config_file: Path to configuration file (relative to project root)
        """
        self.config_file = Path(config_file)
        self.config: AppConfig = self._load_from_file()

    def _load_from_file(self) -> AppConfig:
        """Load configuration from file or create with defaults.

        Returns:
            AppConfig: Loaded or default configuration
        """
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                config = AppConfig(**data)
                logger.info(f"Loaded configuration from {self.config_file}")
                return config
            except Exception as e:
                logger.error(f"Failed to load config from {self.config_file}: {e}")
                logger.info("Using default configuration")
                return AppConfig()
        else:
            logger.info(f"Config file {self.config_file} not found, using defaults")
            return AppConfig()

    def _save_to_file(self) -> None:
        """Persist current configuration to file."""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config.model_dump(), f, indent=2, ensure_ascii=False)
            logger.info(f"Saved configuration to {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to save config to {self.config_file}: {e}")
            raise

    def get_config(self) -> AppConfig:
        """Get current configuration.

        Returns:
            AppConfig: Current configuration
        """
        return self.config

    def update_config(self, config: AppConfig) -> AppConfig:
        """Replace entire configuration.

        Args:
            config: New configuration

        Returns:
            AppConfig: Updated configuration
        """
        self.config = config
        self._save_to_file()
        return self.config

    def update_stage_instructions(
        self, stage: str, instructions: Optional[str]
    ) -> AppConfig:
        """Update instructions for a specific stage.

        Args:
            stage: Stage name (stage1, stage_style, stage2, stage3)
            instructions: New instructions (None to clear)

        Returns:
            AppConfig: Updated configuration

        Raises:
            ValueError: If stage name is invalid
        """
        valid_stages = ["stage1", "stage_style", "stage2", "stage3"]
        if stage not in valid_stages:
            raise ValueError(f"Invalid stage: {stage}. Must be one of {valid_stages}")

        setattr(self.config.stage_instructions, stage, instructions)
        self._save_to_file()
        return self.config

    def update_global_defaults(self, **kwargs) -> AppConfig:
        """Update global default parameters.

        Args:
            **kwargs: Fields to update (num_slides, language, include_titles)

        Returns:
            AppConfig: Updated configuration
        """
        for key, value in kwargs.items():
            if hasattr(self.config.global_defaults, key):
                setattr(self.config.global_defaults, key, value)
        self._save_to_file()
        return self.config

    def update_image_config(self, **kwargs) -> AppConfig:
        """Update image configuration.

        Args:
            **kwargs: Fields to update (width, height, aspect_ratio)

        Returns:
            AppConfig: Updated configuration
        """
        for key, value in kwargs.items():
            if hasattr(self.config.image, key):
                setattr(self.config.image, key, value)
        self._save_to_file()
        return self.config

    def update_style_config(self, **kwargs) -> AppConfig:
        """Update style configuration.

        Args:
            **kwargs: Fields to update (default_font_family, etc.)

        Returns:
            AppConfig: Updated configuration
        """
        for key, value in kwargs.items():
            if hasattr(self.config.style, key):
                setattr(self.config.style, key, value)
        self._save_to_file()
        return self.config

    def reset_to_defaults(self) -> AppConfig:
        """Reset entire configuration to defaults.

        Returns:
            AppConfig: Reset configuration
        """
        self.config = AppConfig()
        self._save_to_file()
        return self.config
