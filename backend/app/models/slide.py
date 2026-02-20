"""Slide models."""

from typing import Optional
from pydantic import BaseModel, Field

from app.models.style import TextStyle


class SlideText(BaseModel):
    """Text content for a slide."""

    title: Optional[str] = Field(default=None, description="Optional slide title")
    body: str = Field(default="", description="Main slide text content")

    def get_full_text(self) -> str:
        """Get combined title and body text for rendering."""
        if self.title:
            return f"{self.title}\n\n{self.body}"
        return self.body


class Slide(BaseModel):
    """Complete slide with all stage data."""

    index: int = Field(ge=0, description="Slide index (0-based)")
    text: SlideText = Field(default_factory=SlideText)
    image_prompt: Optional[str] = Field(
        default=None, description="Generated image prompt"
    )
    background_image_url: Optional[str] = Field(
        default=None,
        description=(
            "Background image as either a served URL path (e.g. /images/uuid.png) "
            "when saved to disk via StorageService, or a raw Base64-encoded PNG string "
            "for direct uploads. Use StorageService.read_image_bytes() to read either form."
        ),
    )
    style: TextStyle = Field(default_factory=TextStyle)
    final_image_url: Optional[str] = Field(
        default=None,
        description=(
            "Final rendered image as either a served URL path (e.g. /images/uuid.png) "
            "when saved to disk via StorageService, or the same as background_image_url "
            "when no text overlay is applied."
        ),
    )
