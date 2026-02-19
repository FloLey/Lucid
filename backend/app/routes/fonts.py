"""Font management routes."""

from fastapi import APIRouter, Depends

from app.dependencies import get_font_manager
from app.services.font_manager import FontManager

router = APIRouter()


@router.get("/")
def list_fonts(font_manager: FontManager = Depends(get_font_manager)):
    """List all available fonts."""
    return {"fonts": font_manager.get_available_fonts()}


@router.get("/mappings")
def get_font_mappings(font_manager: FontManager = Depends(get_font_manager)):
    """Get all supported font family mappings with available weights."""
    mappings = {}
    for family in font_manager.get_available_fonts():
        weights = font_manager.get_font_weights(family)
        mappings[family] = {w: f"{family}-{w}" for w in weights}
    return {"mappings": mappings}


@router.get("/{family}")
def get_font_weights(
    family: str, font_manager: FontManager = Depends(get_font_manager)
):
    """Get available weights for a font family."""
    weights = font_manager.get_font_weights(family)
    return {"family": family, "weights": weights}
