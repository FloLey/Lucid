"""Configuration API routes."""

from typing import Optional, Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.config import (
    AppConfig,
    PromptsConfig,
    StageInstructionsConfig,
    GlobalDefaultsConfig,
    ImageConfig,
    StyleConfig,
)
from app.services.config_manager import config_manager
from app.services.prompt_validator import validate_all_prompts

router = APIRouter()


# Request models
class UpdateStageInstructionsRequest(BaseModel):
    """Request to update stage instructions."""
    stage: str = Field(..., description="Stage name (stage1, stage_style, stage2, stage3)")
    instructions: Optional[str] = Field(None, description="Instructions (None to clear)")


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
async def get_config():
    """Get complete configuration.

    Returns:
        ConfigResponse: Current configuration
    """
    return ConfigResponse(config=config_manager.get_config())


@router.put("", response_model=ConfigResponse)
async def update_config(config: AppConfig):
    """Replace entire configuration.

    Note: This does NOT include prompts. Use /api/prompts to edit prompt files.

    Args:
        config: New configuration

    Returns:
        ConfigResponse: Updated configuration
    """
    try:
        updated_config = config_manager.update_config(config)
        return ConfigResponse(config=updated_config)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Prompts are now managed via /api/prompts endpoints (edit .prompt files directly)


@router.patch("/stage-instructions", response_model=ConfigResponse)
async def update_stage_instructions(request: UpdateStageInstructionsRequest):
    """Update instructions for a specific stage.

    Args:
        request: Stage and instructions

    Returns:
        ConfigResponse: Updated configuration
    """
    try:
        updated_config = config_manager.update_stage_instructions(
            request.stage,
            request.instructions
        )
        return ConfigResponse(config=updated_config)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/global-defaults", response_model=ConfigResponse)
async def update_global_defaults(request: UpdateGlobalDefaultsRequest):
    """Update global default parameters.

    Args:
        request: Global defaults to update

    Returns:
        ConfigResponse: Updated configuration
    """
    try:
        # Only include non-None values
        updates = {k: v for k, v in request.model_dump().items() if v is not None}
        updated_config = config_manager.update_global_defaults(**updates)
        return ConfigResponse(config=updated_config)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/image", response_model=ConfigResponse)
async def update_image_config(request: UpdateImageConfigRequest):
    """Update image configuration.

    Args:
        request: Image config to update

    Returns:
        ConfigResponse: Updated configuration
    """
    try:
        # Only include non-None values
        updates = {k: v for k, v in request.model_dump().items() if v is not None}
        updated_config = config_manager.update_image_config(**updates)
        return ConfigResponse(config=updated_config)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/style", response_model=ConfigResponse)
async def update_style_config(request: UpdateStyleConfigRequest):
    """Update style configuration.

    Args:
        request: Style config to update

    Returns:
        ConfigResponse: Updated configuration
    """
    try:
        # Only include non-None values
        updates = {k: v for k, v in request.model_dump().items() if v is not None}
        updated_config = config_manager.update_style_config(**updates)
        return ConfigResponse(config=updated_config)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reset", response_model=ConfigResponse)
async def reset_config():
    """Reset entire configuration to defaults.

    Returns:
        ConfigResponse: Reset configuration
    """
    try:
        updated_config = config_manager.reset_to_defaults()
        return ConfigResponse(config=updated_config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Prompt validation moved to /api/prompts/validate
