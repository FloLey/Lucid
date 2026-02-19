"""Pytest configuration and fixtures."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.main import app


def run_async(coro):
    """Helper to run async functions in sync test context."""
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)
