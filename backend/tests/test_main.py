"""Tests for main application setup."""


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


def test_stage_placeholders(client):
    """Test all stage placeholder endpoints are reachable."""
    stages = [
        ("/api/stage1/placeholder", 1),
        ("/api/stage2/placeholder", 2),
        ("/api/stage3/placeholder", 3),
        ("/api/stage4/placeholder", 4),
    ]
    for endpoint, stage_num in stages:
        response = client.get(endpoint)
        assert response.status_code == 200
        data = response.json()
        assert data["stage"] == stage_num


def test_export_placeholder(client):
    """Test export placeholder endpoint."""
    response = client.get("/api/export/placeholder")
    assert response.status_code == 200
    data = response.json()
    assert data["feature"] == "export"


def test_projects_list(client):
    """Test projects list endpoint."""
    response = client.get("/api/projects/")
    assert response.status_code == 200
    data = response.json()
    assert "projects" in data
