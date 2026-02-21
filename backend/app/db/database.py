"""Async SQLAlchemy database engine and session factory."""

import os
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

# Default DB path: /app/data/lucid.db (inside Docker named volume)
# For tests, override with LUCID_DB_URL environment variable.
_default_db_path = Path("/app/data/lucid.db")
_db_url = os.getenv("LUCID_DB_URL", f"sqlite+aiosqlite:///{_default_db_path}")


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


def create_engine(db_url: str = _db_url) -> AsyncEngine:
    """Create and return the async SQLAlchemy engine."""
    return create_async_engine(
        db_url,
        connect_args={"check_same_thread": False},
        echo=False,
    )


# Module-level engine and session factory (overridable in tests)
engine: AsyncEngine = create_engine()
async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False
)


async def get_db() -> AsyncSession:
    """FastAPI dependency: yield an async DB session."""
    async with async_session_factory() as session:
        yield session


async def init_db(eng: AsyncEngine | None = None) -> None:
    """Create all tables if they don't exist."""
    from app.db import models as _  # noqa: F401 — ensure models are registered

    target = eng or engine
    async with target.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
