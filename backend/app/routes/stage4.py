"""Stage 4 routes - Typography/Layout rendering."""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.stage4_service import stage4_service

router = APIRouter()


class ApplyTextRequest(BaseModel):
    """Request to apply text to images."""

    session_id: str
    use_ai_suggestions: bool = Field(default=True)


class ApplyTextSingleRequest(BaseModel):
    """Request to apply text to a single image."""

    session_id: str
    slide_index: int = Field(ge=0)


class SuggestStyleRequest(BaseModel):
    """Request to get AI style suggestions."""

    session_id: str
    slide_index: int = Field(ge=0)


class UpdateStyleRequest(BaseModel):
    """Request to update style properties."""

    session_id: str
    slide_index: int = Field(ge=0)
    style: Dict[str, Any] = Field(description="Style properties to update")


class ApplyStyleAllRequest(BaseModel):
    """Request to apply style to all slides."""

    session_id: str
    style: Dict[str, Any] = Field(description="Style properties to apply")


@router.post("/apply-all")
async def apply_text_to_all(request: ApplyTextRequest):
    """Apply text styling to all slide images."""
    session = await stage4_service.apply_text_to_all_images(
        session_id=request.session_id,
        use_ai_suggestions=request.use_ai_suggestions,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or no slides")
    return {"session": session.model_dump()}


@router.post("/apply")
async def apply_text_to_image(request: ApplyTextSingleRequest):
    """Apply text styling to a single slide image."""
    session = await stage4_service.apply_text_to_image(
        session_id=request.session_id,
        slide_index=request.slide_index,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session or slide not found")
    return {"session": session.model_dump()}


@router.post("/suggest")
async def suggest_style(request: SuggestStyleRequest):
    """Get AI suggestions for text styling."""
    session = await stage4_service.suggest_style(
        session_id=request.session_id,
        slide_index=request.slide_index,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session or slide not found")
    return {"session": session.model_dump()}


@router.post("/update-style")
async def update_style(request: UpdateStyleRequest):
    """Update style properties for a slide."""
    session = stage4_service.update_style(
        session_id=request.session_id,
        slide_index=request.slide_index,
        style_updates=request.style,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session or slide not found")
    return {"session": session.model_dump()}


@router.post("/apply-style-all")
async def apply_style_to_all(request: ApplyStyleAllRequest):
    """Apply style updates to all slides."""
    session = stage4_service.apply_style_to_all(
        session_id=request.session_id,
        style_updates=request.style,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or no slides")
    return {"session": session.model_dump()}


@router.get("/presets")
async def get_presets():
    """Get available style presets."""
    presets = {
        "modern": {
            "font_family": "Inter",
            "font_weight": 700,
            "font_size_px": 72,
            "text_color": "#FFFFFF",
            "alignment": "center",
            "stroke": {"enabled": True, "width_px": 2, "color": "#000000"},
        },
        "bold": {
            "font_family": "Oswald",
            "font_weight": 700,
            "font_size_px": 80,
            "text_color": "#FFFFFF",
            "alignment": "center",
            "stroke": {"enabled": True, "width_px": 3, "color": "#000000"},
        },
        "elegant": {
            "font_family": "Playfair Display",
            "font_weight": 600,
            "font_size_px": 64,
            "text_color": "#FFFFFF",
            "alignment": "center",
            "shadow": {"enabled": True, "dx": 2, "dy": 2, "blur": 4, "color": "#00000080"},
        },
        "minimal": {
            "font_family": "Roboto",
            "font_weight": 400,
            "font_size_px": 56,
            "text_color": "#FFFFFF",
            "alignment": "left",
            "box": {"x_pct": 0.1, "y_pct": 0.6, "w_pct": 0.8, "h_pct": 0.3},
        },
        "impact": {
            "font_family": "Montserrat",
            "font_weight": 700,
            "font_size_px": 88,
            "text_color": "#FFFF00",
            "alignment": "center",
            "stroke": {"enabled": True, "width_px": 4, "color": "#000000"},
        },
    }
    return {"presets": presets}


@router.get("/placeholder")
async def placeholder():
    """Placeholder endpoint for backwards compatibility."""
    return {"stage": 4, "status": "active"}
