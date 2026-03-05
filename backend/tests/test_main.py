"""Tests for main application setup."""

from unittest.mock import patch

from app.dependencies import container
from app.services.gemini_service import GeminiError
from tests.conftest import run_async


def test_root_endpoint(client):
    """Test the root health check endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "Lucid API" in data["message"]


def test_health_endpoint(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_cors_headers(client):
    """Test CORS headers are present."""
    response = client.options(
        "/",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    # FastAPI returns 200 for OPTIONS with CORS
    assert response.status_code == 200


def test_projects_list(client):
    """Test projects list endpoint."""
    response = client.get("/api/projects/")
    assert response.status_code == 200
    data = response.json()
    assert "projects" in data


def test_gemini_error_returns_503(client):
    """GeminiError raised inside a route handler must be caught globally → HTTP 503."""
    create_resp = client.post("/api/projects/", json={})
    project_id = create_resp.json()["project"]["project_id"]

    with patch.object(
        container.stage_draft,
        "generate_slide_texts",
        side_effect=GeminiError("Gemini is unavailable"),
    ):
        response = client.post(
            "/api/stage-draft/generate",
            json={
                "project_id": project_id,
                "draft_text": "Some draft text",
            },
        )

    assert response.status_code == 503
    assert "Gemini is unavailable" in response.json()["detail"]


def test_rate_limiter_returns_429(client):
    """Exceeding the per-IP rate limit returns HTTP 429."""
    from app.main import _limiter

    # Fill the hit list to the maximum in the current window
    _limiter._hits.clear()
    import time
    now = time.monotonic()
    ip = "testclient"
    _limiter._hits[ip] = [now] * _limiter._max

    response = client.get("/api/projects/")
    assert response.status_code == 429
    assert "Too many requests" in response.json()["detail"]

    # Clean up so other tests are not affected
    _limiter._hits.clear()


def test_info_endpoint_returns_200(client):
    """GET /api/info returns HTTP 200."""
    response = client.get("/api/info")
    assert response.status_code == 200


def test_info_endpoint_has_version(client):
    """GET /api/info includes the app version."""
    response = client.get("/api/info")
    assert response.json()["version"] == "0.2.0"


def test_info_endpoint_commit_fields_present(client):
    """GET /api/info always returns all commit fields (may be None when git unavailable)."""
    response = client.get("/api/info")
    data = response.json()
    for field in ("commit_hash", "commit_short", "commit_date"):
        assert field in data
        assert data[field] is None or isinstance(data[field], str)
