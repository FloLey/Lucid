"""Chat interface routes."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/placeholder")
async def placeholder():
    """Placeholder endpoint."""
    return {"feature": "chat", "status": "placeholder"}
