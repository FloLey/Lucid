"""Stage 1 service - Draft to Slide texts transformation."""

from __future__ import annotations
import asyncio
import logging
from typing import Optional, TYPE_CHECKING

from app.models.slide import Slide, SlideText
from app.models.project import ProjectState
from app.services.prompt_loader import PromptLoader

if TYPE_CHECKING:
    from app.services.project_manager import ProjectManager
    from app.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)


class Stage1Service:
    """Service for Stage 1: Draft to Slide texts transformation."""

    project_manager: ProjectManager
    gemini_service: GeminiService

    def __init__(
        self,
        project_manager: Optional[ProjectManager] = None,
        gemini_service: Optional[GeminiService] = None,
        prompt_loader: Optional[PromptLoader] = None,
    ):
        if not project_manager:
            raise ValueError("project_manager dependency is required")
        if not gemini_service:
            raise ValueError("gemini_service dependency is required")

        self.project_manager = project_manager
        self.gemini_service = gemini_service
        self.prompt_loader = prompt_loader or PromptLoader()

    @staticmethod
    def _build_title_instruction(include_titles: bool) -> str:
        if include_titles:
            return "Each slide MUST have both a title and body."
        return "Each slide should only have body text (no titles)."

    @staticmethod
    def _build_slide_format(include_titles: bool) -> str:
        if include_titles:
            return '"title" (string) and "body" (string)'
        return '"body" (string) only'

    @staticmethod
    def _build_response_format(include_titles: bool) -> str:
        if include_titles:
            return '{"slides": [{"title": "Hook", "body": "Grab attention here"}, ...]}'
        return '{"slides": [{"body": "First slide content"}, ...]}'

    async def generate_slide_texts(
        self,
        project_id: str,
        draft_text: str,
        num_slides: Optional[int] = None,
        include_titles: bool = True,
        additional_instructions: Optional[str] = None,
        language: str = "English",
    ) -> Optional[ProjectState]:
        """Generate slide texts from a draft."""
        project = await self.project_manager.get_project(project_id)
        if not project:
            return None

        # Store inputs
        project.draft_text = draft_text
        project.num_slides = num_slides
        project.include_titles = include_titles
        project.additional_instructions = additional_instructions
        project.language = language

        if num_slides is not None:
            num_slides_instruction = f"Generate exactly {num_slides} slides."
        else:
            num_slides_instruction = (
                "Choose the optimal number of slides based on the content "
                "(maximum 10 slides)."
            )

        language_instruction = f"Write ALL slide content in {language}."
        title_instruction = self._build_title_instruction(include_titles)
        slide_format = self._build_slide_format(include_titles)
        response_format = self._build_response_format(include_titles)

        additional = (
            f"Additional instructions: {additional_instructions}"
            if additional_instructions
            else ""
        )

        prompt_template = self.prompt_loader.resolve_prompt(project, "slide_generation")

        prompt = prompt_template.format(
            num_slides_instruction=num_slides_instruction,
            language_instruction=language_instruction,
            title_instruction=title_instruction,
            additional_instructions=additional,
            draft=draft_text,
            slide_format=slide_format,
            response_format=response_format,
        )

        result = await self.gemini_service.generate_json(
            prompt, caller="stage1_service.generate_slide_texts"
        )

        slides_data = result.get("slides", [])
        project.slides = []

        max_slides = num_slides if num_slides is not None else 10

        for i, slide_data in enumerate(slides_data[:max_slides]):
            slide = Slide(
                index=i,
                text=SlideText(
                    title=slide_data.get("title") if include_titles else None,
                    body=slide_data.get("body", ""),
                ),
            )
            project.slides.append(slide)

        if num_slides is not None:
            while len(project.slides) < num_slides:
                project.slides.append(
                    Slide(
                        index=len(project.slides),
                        text=SlideText(
                            body=f"Slide {len(project.slides) + 1} content"
                        ),
                    )
                )

        project.num_slides = len(project.slides)

        await self.project_manager.update_project(project)

        # Fire background task to auto-name the project from slide content
        if project.name == "Untitled Project":
            asyncio.create_task(
                self._generate_project_title(project.project_id)
            )

        return project

    async def _generate_project_title(self, project_id: str) -> None:
        """Background task: generate and set a descriptive project title."""
        try:
            project = await self.project_manager.get_project(project_id)
            if not project or project.name != "Untitled Project":
                return

            slides_summary = "\n".join(
                f"Slide {s.index + 1}: {s.text.get_full_text()[:120]}"
                for s in project.slides[:6]
            )

            prompt_template = self.prompt_loader.resolve_prompt(project, "generate_project_title")
            prompt = prompt_template.format(slides_summary=slides_summary)

            result = await self.gemini_service.generate_json(
                prompt, caller="stage1_service._generate_project_title"
            )
            title = result.get("title", "").strip()
            if title and len(title) <= 80:
                await self.project_manager.rename_project(project_id, title)
        except Exception:
            logger.exception("Background title generation failed for %s", project_id)

    async def regenerate_all_slide_texts(
        self,
        project_id: str,
    ) -> Optional[ProjectState]:
        """Regenerate all slide texts using stored inputs."""
        project = await self.project_manager.get_project(project_id)
        if not project or not project.draft_text:
            return None

        return await self.generate_slide_texts(
            project_id=project_id,
            draft_text=project.draft_text,
            num_slides=project.num_slides,
            include_titles=project.include_titles,
            additional_instructions=project.additional_instructions,
            language=project.language,
        )

    async def regenerate_slide_text(
        self,
        project_id: str,
        slide_index: int,
        instruction: Optional[str] = None,
    ) -> Optional[ProjectState]:
        """Regenerate a single slide text."""
        project = await self.project_manager.get_project(project_id)
        if not project or slide_index >= len(project.slides):
            return None

        instruction_text = (
            f"\nSpecific instruction: {instruction}" if instruction else ""
        )

        language_instruction = f"Write ALL slide content in {project.language}."

        title_instruction = (
            "Include both title and body."
            if project.include_titles
            else "Only provide body text."
        )
        response_format = '{"title": "...", "body": "..."}'

        all_slides_parts = []
        for i, s in enumerate(project.slides):
            marker = " ← CURRENT SLIDE" if i == slide_index else ""
            all_slides_parts.append(f"Slide {i + 1}: {s.text.get_full_text()}{marker}")
        all_slides_context = "\n".join(all_slides_parts)

        prompt_template = self.prompt_loader.resolve_prompt(project, "regenerate_single_slide")

        prompt = prompt_template.format(
            draft_text=project.draft_text,
            language_instruction=language_instruction,
            all_slides_context=all_slides_context,
            current_text=project.slides[slide_index].text.get_full_text(),
            instruction_text=instruction_text,
            title_instruction=title_instruction,
            response_format=response_format,
        )

        result = await self.gemini_service.generate_json(
            prompt, caller="stage1_service.regenerate_slide_text"
        )

        if result:
            project.slides[slide_index].text = SlideText(
                title=result.get("title") if project.include_titles else None,
                body=result.get(
                    "body", project.slides[slide_index].text.body
                ),
            )
            await self.project_manager.update_project(project)

        return project

    async def update_slide_text(
        self,
        project_id: str,
        slide_index: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
    ) -> Optional[ProjectState]:
        """Manually update a slide's text."""
        project = await self.project_manager.get_project(project_id)
        if not project or slide_index >= len(project.slides):
            return None

        slide = project.slides[slide_index]
        if title is not None:
            slide.text.title = title
        if body is not None:
            slide.text.body = body

        await self.project_manager.update_project(project)
        return project
