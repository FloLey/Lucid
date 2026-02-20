"""Centralized prompt template I/O — read, write, list."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from app.models.project import ProjectState

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"

# Canonical map of prompt names to filenames
PROMPT_FILES: Dict[str, str] = {
    "slide_generation": "slide_generation.prompt",
    "style_proposal": "style_proposal.prompt",
    "generate_single_image_prompt": "generate_single_image_prompt.prompt",
    "regenerate_single_slide": "regenerate_single_slide.prompt",
}


def load_prompt_file(filename: str) -> str:
    """
    Load a raw prompt string from a file in the prompts directory.

    Args:
        filename: The name of the file to load.

    Returns:
        The file content as a string, or an empty string if loading fails.
    """
    prompt_path = PROMPTS_DIR / filename
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to load prompt file {filename}: {e}")
        return ""


class PromptLoader:
    """Service for loading and saving prompt templates from the file system.

    Prompt contents are cached in memory at initialisation so that
    ``resolve_prompt`` — the hot path called on every generation request —
    never blocks the async event loop with synchronous file I/O.
    The cache is kept up-to-date whenever ``save`` writes a new version.
    """

    def __init__(self) -> None:
        self._cache: Dict[str, str] = {}
        self._load_into_cache()

    def _load_into_cache(self) -> None:
        """Pre-load all registered prompt files into memory."""
        for name, filename in PROMPT_FILES.items():
            self._cache[name] = load_prompt_file(filename)

    def load(self, filename: str) -> str:
        """Load a prompt from the prompts directory."""
        return load_prompt_file(filename)

    def load_all(self) -> Dict[str, str]:
        """Load all registered prompt files.

        Returns:
            Dict mapping prompt names to their content.

        Raises:
            IOError: If any prompt file cannot be read.
        """
        prompts: Dict[str, str] = {}
        for name, filename in PROMPT_FILES.items():
            filepath = PROMPTS_DIR / filename
            with open(filepath, "r", encoding="utf-8") as f:
                prompts[name] = f.read()
        return prompts

    def save(self, prompt_name: str, content: str) -> None:
        """Write content to a prompt file and update the in-memory cache.

        Args:
            prompt_name: Registered prompt name (e.g. "slide_generation").
            content: New prompt content.

        Raises:
            KeyError: If prompt_name is not registered.
            IOError: If file cannot be written.
        """
        if prompt_name not in PROMPT_FILES:
            raise KeyError(f"Unknown prompt: {prompt_name}")
        filepath = PROMPTS_DIR / PROMPT_FILES[prompt_name]
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        self._cache[prompt_name] = content

    def resolve_prompt(self, project: ProjectState, name: str) -> str:
        """Return prompt from project config override, falling back to cache.

        Uses the in-memory cache for the fallback to avoid blocking the async
        event loop with synchronous file I/O on every generation request.

        Args:
            project: The current project (may carry per-project prompt overrides).
            name: Logical prompt name without extension (e.g. "slide_generation").

        Returns:
            Prompt string — project-specific override if set, else cached content.
        """
        return project.project_config.get_prompt(name) or self._cache.get(name, "")

    def is_known(self, prompt_name: str) -> bool:
        """Check if a prompt name is registered."""
        return prompt_name in PROMPT_FILES
