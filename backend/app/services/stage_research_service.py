"""Stage Research service — Grounded chat and draft extraction."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from app.models.project import MAX_STAGES, ProjectState
from app.services.prompt_loader import PromptLoader

if TYPE_CHECKING:
    from app.services.project_manager import ProjectManager
    from app.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

_RESEARCH_SYSTEM_PROMPT = (
    "You are a creative research assistant helping the user brainstorm and gather "
    "information for a social-media carousel. Be concise, insightful, and factual. "
    "Use Google Search to ground your answers in up-to-date information when relevant."
)


class StageResearchService:
    """Service for Stage Research: grounded chat and draft extraction."""

    def __init__(
        self,
        project_manager: Optional[ProjectManager] = None,
        gemini_service: Optional[GeminiService] = None,
        prompt_loader: Optional[PromptLoader] = None,
    ) -> None:
        if not project_manager:
            raise ValueError("project_manager dependency is required")
        if not gemini_service:
            raise ValueError("gemini_service dependency is required")

        self.project_manager = project_manager
        self.gemini_service = gemini_service
        self.prompt_loader = prompt_loader or PromptLoader()

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------

    async def send_message(
        self,
        project_id: str,
        message: str,
    ) -> Optional[ProjectState]:
        """Append a user message to chat_history, get a grounded AI reply, save.

        The conversation is stored as a list of
        ``{"role": "user"|"model", "content": "..."}`` dicts inside
        ``project.chat_history``.
        """
        project = await self.project_manager.get_project(project_id)
        if not project:
            return None

        # Append user turn first
        user_turn: Dict[str, Any] = {"role": "user", "content": message}
        project.chat_history.append(user_turn)

        # Pass the history *before* the new message (the service appends it)
        history_so_far: List[Dict[str, Any]] = project.chat_history[:-1]

        try:
            reply = await self.gemini_service.generate_chat_response(
                history=history_so_far,
                message=message,
                system_instruction=_RESEARCH_SYSTEM_PROMPT,
                use_search_grounding=True,
            )
        except Exception as exc:
            logger.error("Research chat generation failed: %s", exc, exc_info=True)
            # Remove the user turn we already appended so the state stays consistent
            project.chat_history.pop()
            raise

        model_turn: Dict[str, Any] = {"role": "model", "content": reply}
        project.chat_history.append(model_turn)

        await self.project_manager.update_project(project)
        return project

    # ------------------------------------------------------------------
    # Extract draft
    # ------------------------------------------------------------------

    async def extract_draft(
        self,
        project_id: str,
        research_instructions: Optional[str] = None,
    ) -> Optional[ProjectState]:
        """Summarise the chat history into a draft text and advance to Stage Draft.

        After this call ``project.draft_text`` is populated and
        ``project.current_stage`` is set to 2 (Stage Draft).
        """
        project = await self.project_manager.get_project(project_id)
        if not project:
            return None

        if research_instructions is not None:
            project.research_instructions = research_instructions

        # Build a readable transcript of the conversation
        transcript_lines: List[str] = []
        for turn in project.chat_history:
            role_label = "User" if turn.get("role") == "user" else "AI"
            transcript_lines.append(f"{role_label}: {turn.get('content', '')}")
        transcript = "\n\n".join(transcript_lines)

        instructions_block = (
            f"User instructions: {project.research_instructions}"
            if project.research_instructions
            else "No specific formatting instructions provided — use your best judgment."
        )

        prompt_template = self.prompt_loader.resolve_prompt(
            project, "generate_draft_from_research"
        )
        prompt = prompt_template.format(
            transcript=transcript,
            instructions=instructions_block,
        )

        draft_text = await self.gemini_service.generate_text(
            prompt,
            caller="stage_research_service.extract_draft",
        )

        project.draft_text = draft_text.strip()

        # Advance to Stage Draft (stage 2)
        if project.current_stage < 2:
            project.current_stage = 2

        await self.project_manager.update_project(project)
        return project
