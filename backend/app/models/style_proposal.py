"""Style proposal model for Stage 2 (Style selection)."""

from typing import Optional
from pydantic import BaseModel, Field


class StyleProposal(BaseModel):
    """A style proposal with description and preview image."""

    index: int = Field(description="Proposal index")
    description: str = Field(description="Human-readable style description")
    image_prompt: str = Field(default="", description="Image prompt used for preview generation")
    preview_image: Optional[str] = Field(default=None, description="Base64 preview image (display only)")
