"""Configuration API routes."""

from typing import Optional, Dict
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.models.config import AppConfig
from app.dependencies import get_config_manager
from app.services.config_manager import ConfigManager
from app.routes.utils import execute_config_action

router = APIRouter()


# Request models
class UpdateStageInstructionsRequest(BaseModel):
    """Request to update stage instructions."""

    stage: str = Field(
        ..., description="Stage name (stage1, stage_style, stage2, stage3)"
    )
    instructions: Optional[str] = Field(
        None, description="Instructions (None to clear)"
    )


class UpdateGlobalDefaultsRequest(BaseModel):
    """Request to update global defaults."""

    num_slides: Optional[int] = Field(None, ge=1, le=10)
    language: Optional[str] = None
    include_titles: Optional[bool] = None


class UpdateImageConfigRequest(BaseModel):
    """Request to update image config."""

    width: Optional[int] = Field(None, ge=256, le=4096)
    height: Optional[int] = Field(None, ge=256, le=4096)
    aspect_ratio: Optional[str] = None


class UpdateStyleConfigRequest(BaseModel):
    """Request to update style config."""

    default_font_family: Optional[str] = None
    default_font_weight: Optional[int] = Field(None, ge=100, le=900)
    default_font_size_px: Optional[int] = Field(None, ge=12, le=200)
    default_text_color: Optional[str] = None
    default_alignment: Optional[str] = None


# Response models
class ConfigResponse(BaseModel):
    """Standard config response."""

    config: AppConfig


class ValidatePromptsRequest(BaseModel):
    """Request to validate prompts."""

    prompts: Dict[str, str]


class ValidatePromptsResponse(BaseModel):
    """Response from prompt validation."""

    valid: bool
    errors: Dict[str, str]  # Maps prompt name to error message
    warnings: Dict[str, str]  # Maps prompt name to warning message


@router.get("", response_model=ConfigResponse)
def get_config(config_manager: ConfigManager = Depends(get_config_manager)):
    """Get complete configuration."""
    return ConfigResponse(config=config_manager.get_config())


@router.put("", response_model=ConfigResponse)
def update_config(
    config: AppConfig, config_manager: ConfigManager = Depends(get_config_manager)
):
    """Replace entire configuration.

    Note: This does NOT include prompts. Use /api/prompts to edit prompt files.
    """
    return execute_config_action(
        lambda: ConfigResponse(config=config_manager.update_config(config)),
        "Failed to update config",
    )


# Prompts are now managed via /api/prompts endpoints (edit .prompt files directly)


@router.patch("/stage-instructions", response_model=ConfigResponse)
def update_stage_instructions(
    request: UpdateStageInstructionsRequest,
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """Update instructions for a specific stage."""
    return execute_config_action(
        lambda: ConfigResponse(
            config=config_manager.update_stage_instructions(
                request.stage, request.instructions
            )
        ),
        "Failed to update stage instructions",
    )


@router.patch("/global-defaults", response_model=ConfigResponse)
def update_global_defaults(
    request: UpdateGlobalDefaultsRequest,
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """Update global default parameters."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    return execute_config_action(
        lambda: ConfigResponse(config=config_manager.update_global_defaults(**updates)),
        "Failed to update global defaults",
    )


@router.patch("/image", response_model=ConfigResponse)
def update_image_config(
    request: UpdateImageConfigRequest,
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """Update image configuration."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    return execute_config_action(
        lambda: ConfigResponse(config=config_manager.update_image_config(**updates)),
        "Failed to update image config",
    )


@router.patch("/style", response_model=ConfigResponse)
def update_style_config(
    request: UpdateStyleConfigRequest,
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """Update style configuration."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    return execute_config_action(
        lambda: ConfigResponse(config=config_manager.update_style_config(**updates)),
        "Failed to update style config",
    )


@router.post("/reset", response_model=ConfigResponse)
def reset_config(config_manager: ConfigManager = Depends(get_config_manager)):
    """Reset entire configuration to defaults."""
    return execute_config_action(
        lambda: ConfigResponse(config=config_manager.reset_to_defaults()),
        "Failed to reset config",
    )


# Prompt validation moved to /api/prompts/validate
