"""Stage Prompts service - Slide texts to Image prompts transformation."""

from __future__ import annotations
import asyncio
import logging
from typing import Optional, TYPE_CHECKING

from app.models.project import ProjectState
from app.services.base_stage_service import BaseStageService
from app.services.prompt_loader import PromptLoader
from app.services.llm_logger import set_project_context

if TYPE_CHECKING:
    from app.services.project_manager import ProjectManager
    from app.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)


class StagePromptsService(BaseStageService):
    """Service for Stage Prompts: Slide texts to Image prompts transformation."""

    project_manager: ProjectManager
    gemini_service: GeminiService

    def __init__(
        self,
        project_manager: Optional[ProjectManager] = None,
        gemini_service: Optional[GeminiService] = None,
        prompt_loader: Optional[PromptLoader] = None,
    ):
        self.project_manager = self._require(project_manager, "project_manager")
        self.gemini_service = self._require(gemini_service, "gemini_service")
        self.prompt_loader = prompt_loader or PromptLoader()

    def _build_slide_prompt(
        self,
        project: ProjectState,
        slide_index: int,
        instruction: Optional[str] = None,
    ) -> str:
        """Build the LLM prompt for generating a visual concepts description."""
        style_instructions = (
            project.image_style_instructions or "Modern, professional, clean aesthetic"
        )
        shared_theme = (
            project.shared_prompt_prefix or "Consistent visual style throughout"
        )

        context_parts = []
        for i, s in enumerate(project.slides):
            marker = " ← CURRENT SLIDE" if i == slide_index else ""
            context_parts.append(f"Slide {i + 1}: {s.text.get_full_text()}{marker}")
        context = "\n".join(context_parts)

        style_instructions_text = (
            f"Style instructions: {style_instructions}" if style_instructions else ""
        )
        instruction_text = (
            f"Additional instruction for this regeneration: {instruction}"
            if instruction
            else ""
        )

        prompt_template = self.prompt_loader.resolve_prompt(project, "generate_single_image_prompt")
        return prompt_template.format(
            slide_text=project.slides[slide_index].text.get_full_text(),
            shared_theme=shared_theme,
            style_instructions_text=style_instructions_text,
            context=context,
            instruction_text=instruction_text,
            response_format='{"prompt": "your slide-specific image prompt here"}',
        )

    async def generate_all_prompts(
        self,
        project_id: str,
        image_style_instructions: Optional[str] = None,
        concurrency_limit: int = 10,
    ) -> Optional[ProjectState]:
        """Generate image prompts for all slides in parallel."""
        set_project_context(project_id)
        project = await self.project_manager.get_project(project_id)
        if not project or not project.slides:
            return None

        if image_style_instructions:
            project.image_style_instructions = image_style_instructions

        sem = asyncio.Semaphore(concurrency_limit)

        async def generate_single_prompt(slide_index: int) -> str:
            async with sem:
                prompt = self._build_slide_prompt(project, slide_index)
                result = await self.gemini_service.generate_json(
                    prompt, caller="stage_prompts_service.generate_single_prompt"
                )
                return result.get(
                    "prompt",
                    f"Abstract professional background for: {project.slides[slide_index].text.body[:50]}",
                )

        prompts = await asyncio.gather(
            *(generate_single_prompt(i) for i in range(len(project.slides)))
        )

        for i, prompt in enumerate(prompts):
            project.slides[i].image_prompt = prompt

        await self.project_manager.update_project(project)
        return project

    async def regenerate_prompt(
        self,
        project_id: str,
        slide_index: int,
        instruction: Optional[str] = None,
    ) -> Optional[ProjectState]:
        """Regenerate image prompt for a single slide."""
        project = await self.project_manager.get_project(project_id)
        if not project or not (0 <= slide_index < len(project.slides)):
            return None

        prompt = self._build_slide_prompt(project, slide_index, instruction=instruction)
        result = await self.gemini_service.generate_json(
            prompt, caller="stage_prompts_service.regenerate_prompt"
        )

        if result.get("prompt"):
            project.slides[slide_index].image_prompt = result["prompt"]
            await self.project_manager.update_project(project)

        return project

    async def update_prompt(
        self,
        project_id: str,
        slide_index: int,
        prompt: str,
    ) -> Optional[ProjectState]:
        """Manually update an image prompt."""
        project = await self.project_manager.get_project(project_id)
        if not project or not (0 <= slide_index < len(project.slides)):
            return None

        project.slides[slide_index].image_prompt = prompt
        await self.project_manager.update_project(project)
        return project

    async def update_style_instructions(
        self,
        project_id: str,
        style_instructions: str,
    ) -> Optional[ProjectState]:
        """Update the shared style instructions."""
        project = await self.project_manager.get_project(project_id)
        if not project:
            return None

        project.image_style_instructions = style_instructions
        await self.project_manager.update_project(project)
        return project
