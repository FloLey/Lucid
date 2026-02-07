"""Session models."""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from app.models.slide import Slide
from app.models.style_proposal import StyleProposal


class SessionState(BaseModel):
    """Complete session state."""

    session_id: str = Field(description="Unique session identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Stage tracking
    current_stage: int = Field(default=1, ge=1, le=5)

    # Stage 1 inputs
    draft_text: str = Field(default="", description="Original draft text")
    num_slides: int = Field(default=5, ge=1, le=20)
    include_titles: bool = Field(default=True)
    additional_instructions: Optional[str] = Field(default=None)
    language: str = Field(default="English", description="Language for generated content")

    # Stage 2 (Style) data
    style_proposals: List[StyleProposal] = Field(default_factory=list)
    selected_style_proposal_index: Optional[int] = Field(default=None)

    # Stage 3 inputs
    image_style_instructions: Optional[str] = Field(default=None)
    shared_prompt_prefix: Optional[str] = Field(default=None)

    # Slides data (populated through stages)
    slides: List[Slide] = Field(default_factory=list)

    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()

    def get_slide(self, index: int) -> Optional[Slide]:
        """Get a slide by index."""
        if 0 <= index < len(self.slides):
            return self.slides[index]
        return None

    def ensure_slides(self, count: int):
        """Ensure at least 'count' slides exist."""
        while len(self.slides) < count:
            self.slides.append(Slide(index=len(self.slides)))


class CreateSessionRequest(BaseModel):
    """Request to create a new session."""

    session_id: str = Field(description="Client-generated session ID")


class SessionResponse(BaseModel):
    """Response containing session state."""

    session: SessionState


class StageAdvanceRequest(BaseModel):
    """Request to advance to the next stage."""

    session_id: str
