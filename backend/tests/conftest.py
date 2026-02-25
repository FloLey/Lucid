"""Pytest configuration and fixtures."""

import asyncio
import os

# Set test DB URL *before* any app modules are imported so database.py
# reads the correct URL at module-load time.
os.environ.setdefault("LUCID_DB_URL", "sqlite+aiosqlite:///./data/test_lucid.db")
# Override image directory so generated images land in the local data folder
# rather than the Docker-only /app/data/images path.
os.environ.setdefault("LUCID_IMAGE_DIR", "./data/images")

import pytest
from fastapi.testclient import TestClient

from app.main import app


def run_async(coro):
    """Helper to run async functions in sync test context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


@pytest.fixture(autouse=True, scope="session")
def setup_test_env():
    """Initialize database and seed defaults for the test session."""
    import os
    from pathlib import Path

    from app.db.database import init_db, engine, Base
    from app.dependencies import container

    # Ensure the data directory exists (SQLite won't create it automatically)
    db_url = os.environ.get("LUCID_DB_URL", "")
    if "///" in db_url:
        db_path = db_url.split("///", 1)[1]
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async def _setup():
        # Drop all tables first to ensure a clean slate between test runs
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

        # Create all tables and seed default templates
        await init_db()
        await container.template_manager.seed_defaults()

    run_async(_setup())


@pytest.fixture
def client():
    """Create a test client for the FastAPI app.

    Clears all projects before each test to ensure isolation.
    """
    from app.dependencies import container

    run_async(container.project_manager.clear_all())
    return TestClient(app)
