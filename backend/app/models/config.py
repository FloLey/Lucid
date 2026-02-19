"""Configuration models for Lucid application."""

from typing import Optional
from pydantic import BaseModel, Field, field_validator

from app.config import IMAGE_WIDTH, IMAGE_HEIGHT, IMAGE_ASPECT_RATIO


class StageInstructionsConfig(BaseModel):
    """Per-stage additional instructions."""

    stage1: Optional[str] = Field(
        default=None, description="Default instructions for Stage 1 (Draft)"
    )
    stage_style: Optional[str] = Field(
        default=None, description="Default instructions for Stage Style"
    )
    stage2: Optional[str] = Field(
        default=None, description="Default instructions for Stage 2 (Prompts)"
    )
    stage3: Optional[str] = Field(
        default=None, description="Default instructions for Stage 3 (Images)"
    )


class GlobalDefaultsConfig(BaseModel):
    """Global default parameters."""

    num_slides: Optional[int] = Field(
        default=5, description="Default number of slides (None = let AI decide)"
    )
    language: str = Field(default="English", description="Default language for content")
    include_titles: bool = Field(
        default=True, description="Include titles in slides by default"
    )

    @field_validator("num_slides")
    @classmethod
    def validate_num_slides(cls, v):
        """Validate that the slide count is within the supported range (1-10)."""
        if v is not None and (v < 1 or v > 10):
            raise ValueError("num_slides must be between 1 and 10 when specified")
        return v


class ImageConfig(BaseModel):
    """Image generation settings."""

    width: int = Field(
        default=IMAGE_WIDTH, ge=256, le=4096, description="Image width in pixels"
    )
    height: int = Field(
        default=IMAGE_HEIGHT, ge=256, le=4096, description="Image height in pixels"
    )
    aspect_ratio: str = Field(
        default=IMAGE_ASPECT_RATIO, description="Aspect ratio for images"
    )


class StyleConfig(BaseModel):
    """Default style/typography settings."""

    default_font_family: str = Field(default="Inter", description="Default font family")
    default_font_weight: int = Field(
        default=700, ge=100, le=900, description="Default font weight"
    )
    default_font_size_px: int = Field(
        default=72, ge=12, le=200, description="Default font size in pixels"
    )
    default_text_color: str = Field(
        default="#FFFFFF", description="Default text color (hex)"
    )
    default_alignment: str = Field(
        default="center", description="Default text alignment"
    )

    # Stroke (outline) defaults
    default_stroke_enabled: bool = Field(
        default=False, description="Enable text stroke/outline by default"
    )
    default_stroke_width_px: int = Field(
        default=2, ge=0, le=20, description="Default stroke width in pixels"
    )
    default_stroke_color: str = Field(
        default="#000000", description="Default stroke color (hex)"
    )


class AppConfig(BaseModel):
    """Complete application configuration.

    Note: Prompts are NOT stored here - they live in .prompt files.
    Use the /api/prompts endpoints to edit them.
    """

    stage_instructions: StageInstructionsConfig = Field(
        default_factory=StageInstructionsConfig
    )
    global_defaults: GlobalDefaultsConfig = Field(default_factory=GlobalDefaultsConfig)
    image: ImageConfig = Field(default_factory=ImageConfig)
    style: StyleConfig = Field(default_factory=StyleConfig)
