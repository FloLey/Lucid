"""SQLAlchemy ORM models for Lucid persistent storage."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.database import Base


class ProjectDB(Base):
    """Persisted project row."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slide_count: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    current_stage: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    project_config: Mapped[Any] = mapped_column(JSON, nullable=False)
    state: Mapped[Any] = mapped_column(JSON, nullable=False)
    thumbnail_b64: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class TemplateDB(Base):
    """Persisted template row."""

    __tablename__ = "templates"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    default_slide_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5
    )
    config: Mapped[Any] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


# ── Concept Matrix tables ─────────────────────────────────────────────────


class MatrixProjectDB(Base):
    """One concept matrix project."""

    __tablename__ = "matrix_projects"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    theme: Mapped[str] = mapped_column(Text, nullable=False)
    n: Mapped[int] = mapped_column(Integer, nullable=False)
    language: Mapped[str] = mapped_column(String, nullable=False, default="English")
    style_mode: Mapped[str] = mapped_column(String, nullable=False, default="neutral")
    include_images: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_mode: Mapped[str] = mapped_column(String, nullable=False, default="theme")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class MatrixCellDB(Base):
    """One cell (row, col) in a concept matrix."""

    __tablename__ = "matrix_cells"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("matrix_projects.id", ondelete="CASCADE"), nullable=False
    )
    row: Mapped[int] = mapped_column(Integer, nullable=False)
    col: Mapped[int] = mapped_column(Integer, nullable=False)
    # Diagonal cells (row == col): concept seed
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
    definition: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Axis descriptors derived from diagonal concept
    row_descriptor: Mapped[str | None] = mapped_column(Text, nullable=True)
    col_descriptor: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Off-diagonal cells: intersection concept
    concept: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Optional image URL
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Cell status: pending | generating | complete | failed
    cell_status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    cell_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
