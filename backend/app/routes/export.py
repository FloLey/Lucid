"""Export routes."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/placeholder")
async def placeholder():
    """Placeholder endpoint."""
    return {"feature": "export", "status": "placeholder"}
