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


@pytest.fixture
def client():
    """Create a test client for the FastAPI app.

    Clears all projects before each test to ensure isolation.
    """
    from app.dependencies import container

    container.project_manager.clear_all()
    return TestClient(app)
