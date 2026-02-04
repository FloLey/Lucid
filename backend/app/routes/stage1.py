"""Stage 1 routes - Draft to Slide texts."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/placeholder")
async def placeholder():
    """Placeholder endpoint."""
    return {"stage": 1, "status": "placeholder"}
