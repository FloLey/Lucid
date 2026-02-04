"""Stage 4 routes - Typography/Layout rendering."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/placeholder")
async def placeholder():
    """Placeholder endpoint."""
    return {"stage": 4, "status": "placeholder"}
