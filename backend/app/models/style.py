"""Style models for typography and layout."""

from pydantic import BaseModel, Field


class BoxStyle(BaseModel):
    """Text box positioning and sizing."""

    x_pct: float = Field(
        default=0.05, ge=0, le=1, description="X position as percentage"
    )
    y_pct: float = Field(
        default=0.15, ge=0, le=1, description="Y position as percentage"
    )
    w_pct: float = Field(default=0.9, ge=0, le=1, description="Width as percentage")
    h_pct: float = Field(default=0.7, ge=0, le=1, description="Height as percentage")
    padding_pct: float = Field(
        default=0.03, ge=0, le=0.5, description="Padding as percentage"
    )


class StrokeStyle(BaseModel):
    """Configuration for text outlines/strokes."""

    enabled: bool = False
    width_px: int = Field(default=2, ge=0, le=20)
    color: str = Field(default="#000000", pattern=r"^#[0-9A-Fa-f]{6}$")


class ShadowStyle(BaseModel):
    """Configuration for text drop-shadow effects."""

    enabled: bool = False
    dx: int = Field(default=2, ge=-20, le=20)
    dy: int = Field(default=2, ge=-20, le=20)
    blur: int = Field(default=4, ge=0, le=20)
    color: str = Field(default="#00000080", pattern=r"^#[0-9A-Fa-f]{6,8}$")


class TextStyle(BaseModel):
    """Complete text styling configuration."""

    font_family: str = Field(default="Inter", description="Font family name")
    font_weight: int = Field(default=700, ge=100, le=900)
    font_size_px: int = Field(default=72, ge=12, le=200)
    body_font_size_px: int = Field(default=40, ge=12, le=200)
    text_color: str = Field(default="#FFFFFF", pattern=r"^#[0-9A-Fa-f]{6,8}$")
    alignment: str = Field(default="center", pattern=r"^(left|center|right)$")
    title_box: BoxStyle = Field(
        default_factory=lambda: BoxStyle(x_pct=0.05, y_pct=0.1, w_pct=0.9, h_pct=0.2)
    )
    body_box: BoxStyle = Field(
        default_factory=lambda: BoxStyle(x_pct=0.05, y_pct=0.35, w_pct=0.9, h_pct=0.55)
    )
    line_spacing: float = Field(default=1.2, ge=0.5, le=3.0)
    stroke: StrokeStyle = Field(default_factory=StrokeStyle)
    shadow: ShadowStyle = Field(default_factory=ShadowStyle)
    max_lines: int = Field(default=12, ge=1, le=20)
    text_enabled: bool = Field(default=True, description="Whether text is rendered on this slide")
