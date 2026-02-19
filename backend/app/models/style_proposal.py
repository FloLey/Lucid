"""Style proposal model for Stage 2 (Style selection)."""

from typing import Optional
from pydantic import BaseModel, Field


class StyleProposal(BaseModel):
    """A style proposal with common visual style prompt and preview image."""

    index: int = Field(description="Proposal index")
    description: str = Field(
        description="Common visual style prompt (used for preview and prepended to all slides)"
    )
    preview_image: Optional[str] = Field(
        default=None, description="Base64 preview image (display only)"
    )
