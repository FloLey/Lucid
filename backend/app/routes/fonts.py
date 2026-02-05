"""Font management routes."""

from fastapi import APIRouter

from app.services.font_manager import font_manager

router = APIRouter()


@router.get("/")
async def list_fonts():
    """List all available fonts."""
    return {"fonts": font_manager.get_available_fonts()}


@router.get("/mappings")
async def get_font_mappings():
    """Get all supported font family mappings with available weights."""
    mappings = {}
    for family in font_manager.get_available_fonts():
        weights = font_manager.get_font_weights(family)
        mappings[family] = {w: f"{family}-{w}" for w in weights}
    return {"mappings": mappings}


@router.get("/{family}")
async def get_font_weights(family: str):
    """Get available weights for a font family."""
    weights = font_manager.get_font_weights(family)
    return {"family": family, "weights": weights}
