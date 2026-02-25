"""Base class shared by all pipeline stage services."""

from __future__ import annotations

from typing import Optional, TypeVar

T = TypeVar("T")


class BaseStageService:
    """Provides common helpers for stage service __init__ validation."""

    @staticmethod
    def _require(value: Optional[T], name: str) -> T:
        """Assert *value* is not None/falsy, raising ValueError otherwise."""
        if not value:
            raise ValueError(f"{name} dependency is required")
        return value  # type: ignore[return-value]
