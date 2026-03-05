"""Pydantic models for the Concept Matrix Generator."""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


# ── Settings ──────────────────────────────────────────────────────────────


class MatrixSettings(BaseModel):
    """Runtime-configurable settings, persisted to matrix_settings.json."""

    text_model: str = Field(default="gemini-2.5-flash")
    image_model: str = Field(default="gemini-2.5-flash-image")
    diagonal_temperature: float = Field(default=0.9)
    axes_temperature: float = Field(default=0.8)
    cell_temperature: float = Field(default=0.7)
    validation_temperature: float = Field(default=0.3)
    max_concurrency: int = Field(default=4, ge=1, le=20)
    max_retries: int = Field(default=3, ge=0, le=5)


# ── Cell ──────────────────────────────────────────────────────────────────


class MatrixCell(BaseModel):
    """Single cell in an n×n matrix (row, col)."""

    id: str
    project_id: str
    row: int
    col: int
    # Diagonal fields (row == col)
    label: Optional[str] = None
    definition: Optional[str] = None
    row_descriptor: Optional[str] = None
    col_descriptor: Optional[str] = None
    # Off-diagonal fields
    concept: Optional[str] = None
    explanation: Optional[str] = None
    # Optional image
    image_url: Optional[str] = None
    # Status
    cell_status: Literal["pending", "generating", "complete", "failed"] = "pending"
    cell_error: Optional[str] = None
    attempts: int = 0


# ── Project ───────────────────────────────────────────────────────────────


class MatrixProject(BaseModel):
    """Full matrix project state."""

    id: str
    name: str
    theme: str
    n: int
    language: str = "English"
    style_mode: str = "neutral"
    include_images: bool = False
    input_mode: str = "theme"
    description: Optional[str] = None
    status: Literal["pending", "generating", "complete", "failed"] = "pending"
    error_message: Optional[str] = None
    cells: List[MatrixCell] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class MatrixProjectCard(BaseModel):
    """Lightweight card for project list."""

    id: str
    name: str
    theme: str
    n: int
    status: Literal["pending", "generating", "complete", "failed"]
    include_images: bool
    created_at: datetime
    updated_at: datetime


# ── Request / Response ────────────────────────────────────────────────────


class CreateMatrixRequest(BaseModel):
    input_mode: Literal["theme", "description"] = Field(default="theme")
    theme: str = Field(default="", max_length=1000)
    description: Optional[str] = Field(default=None, max_length=2000)
    n: int = Field(default=4, ge=2, le=8)
    language: str = Field(default="English", max_length=50)
    style_mode: str = Field(default="neutral", max_length=50)
    include_images: bool = Field(default=False)
    name: Optional[str] = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def validate_input(self) -> "CreateMatrixRequest":
        if self.input_mode == "theme" and len(self.theme.strip()) < 3:
            raise ValueError("theme must be at least 3 characters for theme mode")
        if self.input_mode == "description" and not (self.description or "").strip():
            raise ValueError("description is required for description mode")
        return self


class RegenerateCellRequest(BaseModel):
    extra_instructions: Optional[str] = None
    image_only: bool = False


class MatrixProjectResponse(BaseModel):
    matrix: MatrixProject


class MatrixListResponse(BaseModel):
    matrices: List[MatrixProjectCard]


class MatrixSettingsResponse(BaseModel):
    settings: MatrixSettings


class UpdateMatrixSettingsRequest(BaseModel):
    settings: MatrixSettings
