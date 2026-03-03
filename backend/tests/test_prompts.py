"""Tests for /api/prompts endpoints."""

from app.services.prompt_loader import PROMPT_FILES


def test_get_prompts_returns_all_prompts(client):
    """GET /api/prompts returns a dict of all registered prompt names."""
    response = client.get("/api/prompts")
    assert response.status_code == 200
    data = response.json()
    assert "prompts" in data
    prompts = data["prompts"]
    assert isinstance(prompts, dict)
    # Every registered prompt name should be present
    for name in PROMPT_FILES:
        assert name in prompts, f"Expected prompt '{name}' in response"


def test_get_prompts_values_are_strings(client):
    """GET /api/prompts returns string content for every prompt."""
    response = client.get("/api/prompts")
    assert response.status_code == 200
    prompts = response.json()["prompts"]
    for name, content in prompts.items():
        assert isinstance(content, str), f"Prompt '{name}' content is not a string"
        assert len(content) > 0, f"Prompt '{name}' is unexpectedly empty"


def test_update_prompt_unknown_name_returns_404(client):
    """PUT /api/prompts/{name} with an unregistered name returns 404."""
    response = client.put(
        "/api/prompts/nonexistent_prompt",
        json={"prompt_name": "nonexistent_prompt", "content": "some content"},
    )
    assert response.status_code == 404


def test_update_prompt_known_name_saves(client):
    """PUT /api/prompts/{name} with a registered name and valid content saves successfully."""
    # Use a prompt whose required variables are tracked by the validator.
    # 'style_proposal' requires: num_proposals, slides_text, additional_instructions,
    # response_format — include all of them so validation passes.
    prompt_name = "style_proposal"
    valid_content = (
        "{num_proposals} {slides_text} {additional_instructions} {response_format}"
    )

    # Save original content so we can restore it after the test
    original_content = client.get("/api/prompts").json()["prompts"][prompt_name]

    try:
        response = client.put(
            f"/api/prompts/{prompt_name}",
            json={"prompt_name": prompt_name, "content": valid_content},
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert prompt_name in data["message"]
    finally:
        # Restore original prompt content to avoid corrupting the file for other tests
        client.put(
            f"/api/prompts/{prompt_name}",
            json={"prompt_name": prompt_name, "content": original_content},
        )


def test_update_prompts_patch_unknown_name_returns_400(client):
    """PATCH /api/prompts with an unknown name in batch returns 400."""
    response = client.patch(
        "/api/prompts",
        json={"prompts": {"definitely_unknown_prompt": "content"}},
    )
    assert response.status_code == 400
    assert "Unknown prompt" in response.json()["detail"]


def test_update_prompts_patch_empty_dict(client):
    """PATCH /api/prompts with an empty dict updates 0 prompts gracefully."""
    response = client.patch("/api/prompts", json={"prompts": {}})
    assert response.status_code == 200
    assert "0" in response.json()["message"]


def test_validate_prompts_valid(client):
    """POST /api/prompts/validate with a prompt containing all required vars returns valid=true."""
    # Build a minimal valid slide_generation prompt
    valid_content = (
        "{num_slides_instruction} {language_instruction} {title_instruction} "
        "{additional_instructions} {draft} {slide_format} {response_format}"
    )
    response = client.post(
        "/api/prompts/validate",
        json={"prompts": {"slide_generation": valid_content}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert "slide_generation" not in data["errors"]


def test_validate_prompts_missing_variables(client):
    """POST /api/prompts/validate with missing required vars populates errors dict."""
    # Intentionally omit required variables
    response = client.post(
        "/api/prompts/validate",
        json={"prompts": {"slide_generation": "This prompt has no required variables."}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert "slide_generation" in data["errors"]
    assert "Missing required variables" in data["errors"]["slide_generation"]


def test_validate_prompts_unknown_prompt_name(client):
    """POST /api/prompts/validate for an unknown prompt name is handled gracefully."""
    # Unknown prompt names pass through validate_all_prompts; validate_prompt returns False
    response = client.post(
        "/api/prompts/validate",
        json={"prompts": {"unknown_prompt_xyz": "content here"}},
    )
    # Should return 200 (validation endpoint, not save endpoint)
    assert response.status_code == 200


def test_reset_prompts_returns_501(client):
    """POST /api/prompts/reset always returns 501 (not implemented)."""
    response = client.post("/api/prompts/reset")
    assert response.status_code == 501
