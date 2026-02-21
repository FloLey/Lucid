"""SQLAlchemy ORM models for Lucid persistent storage."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text
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
