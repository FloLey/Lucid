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
    """Get all supported font family mappings."""
    return {"mappings": font_manager.FONT_MAPPINGS}
