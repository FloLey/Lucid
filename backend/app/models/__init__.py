"""Pydantic models for Lucid."""

from app.models.slide import Slide, SlideText
from app.models.style import TextStyle, BoxStyle, StrokeStyle, ShadowStyle
from app.models.style_proposal import StyleProposal
from app.models.config import (
    AppConfig,
    StageInstructionsConfig,
    GlobalDefaultsConfig,
    ImageConfig,
    StyleConfig,
)

__all__ = [
    "Slide",
    "SlideText",
    "TextStyle",
    "BoxStyle",
    "StrokeStyle",
    "ShadowStyle",
    "StyleProposal",
    "AppConfig",
    "StageInstructionsConfig",
    "GlobalDefaultsConfig",
    "ImageConfig",
    "StyleConfig",
]
