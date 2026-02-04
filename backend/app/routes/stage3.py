"""Stage 3 routes - Image prompts to Images."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/placeholder")
async def placeholder():
    """Placeholder endpoint."""
    return {"stage": 3, "status": "placeholder"}
