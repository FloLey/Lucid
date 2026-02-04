"""Stage 2 routes - Slide texts to Image prompts."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/placeholder")
async def placeholder():
    """Placeholder endpoint."""
    return {"stage": 2, "status": "placeholder"}
