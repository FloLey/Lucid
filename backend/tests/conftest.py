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
from typing import List, Optional

from app.main import app, _limiter


def run_async(coro):
    """Helper to run async functions in sync test context."""
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
    Resets the rate limiter so the full test suite never gets throttled.
    """
    from app.dependencies import container

    _limiter._hits.clear()
    run_async(container.project_manager.clear_all())
    return TestClient(app)


# ---------------------------------------------------------------------------
# Shared project factory fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def make_project_with_slides():
    """Factory fixture that creates a project with a configurable set of slides.

    Usage::

        def test_something(make_project_with_slides):
            from app.models.slide import Slide, SlideText
            project = make_project_with_slides(
                slides=[Slide(index=0, text=SlideText(title="T", body="B"))],
                draft_text="my draft",
            )
    """
    from app.dependencies import container
    from app.models.slide import Slide, SlideText

    project_manager = container.project_manager

    def _factory(
        slides: Optional[List] = None,
        draft_text: str = "Test draft content",
        shared_prompt_prefix: Optional[str] = None,
    ):
        run_async(project_manager.clear_all())
        project = run_async(project_manager.create_project())

        if slides is None:
            slides = [
                Slide(index=0, text=SlideText(title="Slide 1", body="Content 1")),
                Slide(index=1, text=SlideText(title="Slide 2", body="Content 2")),
                Slide(index=2, text=SlideText(title="Slide 3", body="Content 3")),
            ]

        project.slides = slides
        project.draft_text = draft_text
        if shared_prompt_prefix is not None:
            project.shared_prompt_prefix = shared_prompt_prefix

        run_async(project_manager.update_project(project))
        return project

    return _factory


@pytest.fixture
def project_with_slides(make_project_with_slides):
    """Shared convenience fixture: a project with 3 generic slides."""
    return make_project_with_slides()
