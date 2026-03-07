"""Base class shared by all pipeline stage services."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Coroutine, List, Optional, TypeVar, Union

from app.services.async_utils import bounded_gather
from app.services.llm_logger import set_project_context
from app.models.style import TextStyle, StrokeStyle

T = TypeVar("T")

# Default maximum number of slide-level operations that run simultaneously.
_DEFAULT_CONCURRENCY = 5


class BaseStageService:
    """Provides common helpers for stage service __init__ validation."""

    @staticmethod
    def _style_from_config(project: Any) -> TextStyle:
        """Build a TextStyle seeded from the project's config defaults."""
        cfg = project.project_config.style
        return TextStyle(
            font_family=cfg.default_font_family,
            font_weight=cfg.default_font_weight,
            font_size_px=cfg.default_font_size_px,
            text_color=cfg.default_text_color,
            alignment=cfg.default_alignment,
            text_enabled=cfg.default_text_enabled,
            stroke=StrokeStyle(
                enabled=cfg.default_stroke_enabled,
                width_px=cfg.default_stroke_width_px,
                color=cfg.default_stroke_color,
            ),
        )

    @staticmethod
    def _require(value: Optional[T], name: str) -> T:
        """Assert *value* is not None/falsy, raising ValueError otherwise."""
        if not value:
            raise ValueError(f"{name} dependency is required")
        return value  # type: ignore[return-value]

    @staticmethod
    def _valid_slide(project: Any, slide_index: int) -> bool:
        """Return True if *project* is not None and *slide_index* is in bounds."""
        return bool(project and 0 <= slide_index < len(project.slides))

    @staticmethod
    async def _batch(
        coros: List[Coroutine[Any, Any, T]],
        limit: int = _DEFAULT_CONCURRENCY,
        return_exceptions: bool = False,
    ) -> List[Union[T, BaseException]]:
        """Run coroutines concurrently with a bounded concurrency limit.

        Thin wrapper around :func:`bounded_gather` that provides a consistent
        call site for all stage services and makes the default concurrency
        explicit.
        """
        return await bounded_gather(coros, limit=limit, return_exceptions=return_exceptions)

    @asynccontextmanager
    async def _project_ctx(
        self, project_id: str
    ) -> AsyncGenerator[Any, None]:
        """Async context manager that fetches a project, sets logging context,
        and auto-saves on clean exit.

        Usage::

            async with self._project_ctx(project_id) as project:
                if project is None:
                    return None
                project.some_field = new_value
            return project

        On normal exit the project is persisted via ``project_manager.update_project``.
        On exception the project is NOT saved (state is not committed on error).
        If ``project_id`` does not map to an existing project, ``None`` is
        yielded and nothing is saved.
        """
        set_project_context(project_id)
        project = await self.project_manager.get_project(project_id)  # type: ignore[attr-defined]
        if project is None:
            yield None
            return
        try:
            yield project
        except Exception:
            raise
        else:
            await self.project_manager.update_project(project)  # type: ignore[attr-defined]
