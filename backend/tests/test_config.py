"""Tests for /api/config endpoints."""


def test_get_config_returns_default_shape(client):
    """GET /api/config returns a well-formed config."""
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "config" in data
    cfg = data["config"]
    assert "stage_instructions" in cfg
    assert "global_defaults" in cfg
    assert "image" in cfg
    assert "style" in cfg


def test_get_config_global_defaults(client):
    """Default global_defaults values are present and sane."""
    response = client.get("/api/config")
    assert response.status_code == 200
    defaults = response.json()["config"]["global_defaults"]
    assert isinstance(defaults["num_slides"], int)
    assert defaults["language"] == "English"
    assert isinstance(defaults["include_titles"], bool)


def test_update_config_full_replace(client):
    """PUT /api/config replaces the entire configuration."""
    # Get current config and make a small change
    current = client.get("/api/config").json()["config"]
    current["global_defaults"]["language"] = "Spanish"
    response = client.put("/api/config", json=current)
    assert response.status_code == 200
    assert response.json()["config"]["global_defaults"]["language"] == "Spanish"


def test_update_config_reset_on_put(client):
    """PUT /api/config with defaults roundtrips correctly."""
    current = client.get("/api/config").json()["config"]
    response = client.put("/api/config", json=current)
    assert response.status_code == 200
    assert response.json()["config"] == current


def test_patch_stage_instructions_valid(client):
    """PATCH /api/config/stage-instructions updates a known stage."""
    payload = {"stage": "stage1", "instructions": "Be concise."}
    response = client.patch("/api/config/stage-instructions", json=payload)
    assert response.status_code == 200
    cfg = response.json()["config"]
    assert cfg["stage_instructions"]["stage1"] == "Be concise."


def test_patch_stage_instructions_clear(client):
    """PATCH /api/config/stage-instructions with None clears the instruction."""
    # First set it
    client.patch(
        "/api/config/stage-instructions",
        json={"stage": "stage2", "instructions": "Some instruction"},
    )
    # Then clear it
    response = client.patch(
        "/api/config/stage-instructions",
        json={"stage": "stage2", "instructions": None},
    )
    assert response.status_code == 200
    cfg = response.json()["config"]
    assert cfg["stage_instructions"]["stage2"] is None


def test_patch_stage_instructions_invalid_stage(client):
    """PATCH /api/config/stage-instructions with an unknown stage returns 400."""
    payload = {"stage": "stage_nonexistent", "instructions": "irrelevant"}
    response = client.patch("/api/config/stage-instructions", json=payload)
    assert response.status_code == 400
    assert "Invalid stage" in response.json()["detail"]


def test_patch_global_defaults_num_slides(client):
    """PATCH /api/config/global-defaults updates num_slides."""
    response = client.patch("/api/config/global-defaults", json={"num_slides": 8})
    assert response.status_code == 200
    assert response.json()["config"]["global_defaults"]["num_slides"] == 8


def test_patch_global_defaults_language(client):
    """PATCH /api/config/global-defaults updates language."""
    response = client.patch("/api/config/global-defaults", json={"language": "French"})
    assert response.status_code == 200
    assert response.json()["config"]["global_defaults"]["language"] == "French"


def test_patch_global_defaults_include_titles(client):
    """PATCH /api/config/global-defaults updates include_titles."""
    response = client.patch(
        "/api/config/global-defaults", json={"include_titles": False}
    )
    assert response.status_code == 200
    assert response.json()["config"]["global_defaults"]["include_titles"] is False


def test_patch_global_defaults_num_slides_too_small(client):
    """PATCH /api/config/global-defaults with num_slides=0 returns 422."""
    response = client.patch("/api/config/global-defaults", json={"num_slides": 0})
    assert response.status_code == 422


def test_patch_image_config_width_height(client):
    """PATCH /api/config/image updates width and height."""
    response = client.patch("/api/config/image", json={"width": 1080, "height": 1350})
    assert response.status_code == 200
    img = response.json()["config"]["image"]
    assert img["width"] == 1080
    assert img["height"] == 1350


def test_patch_image_config_width_too_small(client):
    """PATCH /api/config/image with width below minimum returns 422."""
    response = client.patch("/api/config/image", json={"width": 100})
    assert response.status_code == 422


def test_patch_image_config_width_too_large(client):
    """PATCH /api/config/image with width above maximum returns 422."""
    response = client.patch("/api/config/image", json={"width": 9999})
    assert response.status_code == 422


def test_patch_style_config(client):
    """PATCH /api/config/style updates style fields."""
    payload = {
        "default_font_family": "Roboto",
        "default_font_weight": 400,
        "default_font_size_px": 60,
        "default_text_color": "#000000",
    }
    response = client.patch("/api/config/style", json=payload)
    assert response.status_code == 200
    style = response.json()["config"]["style"]
    assert style["default_font_family"] == "Roboto"
    assert style["default_font_weight"] == 400
    assert style["default_font_size_px"] == 60
    assert style["default_text_color"] == "#000000"


def test_patch_style_config_font_weight_out_of_range(client):
    """PATCH /api/config/style with font weight out of range returns 422."""
    response = client.patch("/api/config/style", json={"default_font_weight": 50})
    assert response.status_code == 422


def test_reset_config_restores_defaults(client):
    """POST /api/config/reset restores default language after a change."""
    # Change language
    client.patch("/api/config/global-defaults", json={"language": "German"})
    changed = client.get("/api/config").json()["config"]["global_defaults"]["language"]
    assert changed == "German"

    # Reset
    response = client.post("/api/config/reset")
    assert response.status_code == 200
    assert response.json()["config"]["global_defaults"]["language"] == "English"


def test_reset_config_clears_stage_instructions(client):
    """POST /api/config/reset clears any custom stage instructions."""
    client.patch(
        "/api/config/stage-instructions",
        json={"stage": "stage1", "instructions": "Custom"},
    )
    response = client.post("/api/config/reset")
    assert response.status_code == 200
    assert response.json()["config"]["stage_instructions"]["stage1"] is None
