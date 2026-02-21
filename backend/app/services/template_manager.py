"""Template management service — CRUD + default seeding."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.database import async_session_factory as _default_session_factory
from app.db.models import TemplateDB
from app.models.project import ProjectConfig, TemplateData
from app.models.config import GlobalDefaultsConfig, StyleConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Carousel template prompts
# ---------------------------------------------------------------------------

_CAROUSEL_PROMPTS = {
    "generate_draft_from_research": """\
You are an expert educator and writer. Your task is to distill a research conversation into a clear, high-quality article draft.
Transcript:
{transcript}
{instructions}
Extract the most valuable insights. Write compelling, well-structured prose that is factual but fun to read. Focus on delivering real value and explaining concepts clearly without using cheap marketing tactics or fluff. Output ONLY the polished draft text.""",

    "slide_generation": """\
You are a skilled writer adapting an article into a multi-part visual presentation.
Given a draft text, {num_slides_instruction}
Draft text:
{draft}
Transform the text into a cohesive, high-quality presentation:
- The Introduction (Slide 1): An engaging but natural introduction to the topic. Do not use aggressive "scroll-stopping" clickbait.
- The Body: Break ideas into logical, well-explained chunks. One core concept per slide.
- The Conclusion: A clear summary of the main takeaway. DO NOT include Call-To-Actions (CTAs).
{language_instruction}
{title_instruction}
{word_count_instruction}
{additional_instructions}
Each slide should have: {slide_format}
Respond purely with valid JSON:
{response_format}""",

    "style_proposal": """\
You are an expert Art Director establishing the visual identity for an elegant presentation.
Given the texts below, propose {num_proposals} distinct, high-end visual art directions.
Slides:
{slides_text}
{additional_instructions}
For each proposal, write a direct image generation prompt detailing the visual aesthetic. Focus on:
- Color Palette: Specific harmonious tones (e.g., muted sage, deep slate, warm terracotta).
- Texture & Medium: (e.g., frosted glass, subtle grain, clean vector, minimalist photography).
- Lighting: (e.g., soft diffused studio light, natural morning sun).
CRITICAL: The style MUST serve as a clean, unobtrusive background for reading text.
Respond with JSON:
{response_format}""",

    "generate_single_image_prompt": """\
Task: Create an image generation prompt for a background asset for ONE slide.
Slide content: {slide_text}
All slides context: {context}
{instruction_text}
Visual Art Direction: "{shared_theme}"
{style_instructions_text}
Create a highly specific image prompt for this slide.
CRITICAL COMPOSITIONAL RULES:
- The image is purely a background. It MUST have clean negative space or smooth areas where text can be easily read.
- Push any abstract shapes or elements to the edges.
- NEVER include any text, UI elements, borders, letters, or watermarks.
Respond with JSON: {response_format}""",
}


# ---------------------------------------------------------------------------
# Painting template prompts
# ---------------------------------------------------------------------------

_PAINTING_PROMPTS = {
    "generate_draft_from_research": """\
You are a conceptual researcher. Synthesize this conversation into a deep, meaningful exploration of a subject that will inspire a painting.
Transcript:
{transcript}
{instructions}
Define the central allegory, the emotional weight, and the historical or philosophical context of the topic. Output ONLY the concept text itself, with no meta-commentary.""",

    "slide_generation": """\
You are a conceptual writer defining the core subject matter for an artwork.
{num_slides_instruction}
Draft text:
{draft}
Distill the text into a single, profound description of the SUBJECT. Focus entirely on *what* is being depicted—the story, the symbolism, and the emotional landscape. Do not describe the art style, brushstrokes, or lighting here; focus only on the meaning and the subjects in the scene.
{language_instruction}
{title_instruction}
{word_count_instruction}
{additional_instructions}
Each slide should have: {slide_format}
Respond purely with valid JSON:
{response_format}""",

    "style_proposal": """\
You are a renowned art historian and Art Director.
Given the artwork's subject below, propose {num_proposals} distinct, breathtaking fine art mediums and styles.
Subject:
{slides_text}
{additional_instructions}
For each proposal, write a highly detailed visual directive focusing entirely on the execution:
- Medium & Brushwork: (e.g., thick impasto oil on canvas, ethereal watercolor, detailed tempera).
- Lighting Technique: (e.g., dramatic Chiaroscuro, flat gold-leaf, dappled light).
- Color Theory: (e.g., monochromatic umber, vibrant Fauvist complementary colors).
This is for a standalone masterpiece, not a background.
Respond with JSON:
{response_format}""",

    "generate_single_image_prompt": """\
Task: Act as an elite AI art prompt engineer. Construct a complex, vivid prompt to generate a breathtaking painting.
Subject: {slide_text}
{context}
{instruction_text}
Artistic Style & Medium to apply: "{shared_theme}"
{style_instructions_text}
Create a master-level image generation prompt that fuses the subject with the artistic style.
- Reinforce the physical properties of the paint and canvas (e.g., visible brushstrokes, canvas texture).
- This is a complete, standalone artwork. Do NOT leave empty negative space for text.
- EXPLICITLY FORBID: text, signatures, watermarks, borders, and UI elements.
Respond with JSON: {response_format}""",
}


def _load_default_prompts() -> Dict[str, str]:
    """Load all known .prompt files into a dict keyed by stem."""
    from app.services.prompt_loader import PromptLoader

    loader = PromptLoader()
    all_prompts = loader.load_all()
    return {name: content for name, content in all_prompts.items()}


def _row_to_data(row: TemplateDB) -> TemplateData:
    return TemplateData(
        id=row.id,
        name=row.name,
        default_slide_count=row.default_slide_count,
        config=ProjectConfig.model_validate(row.config),
        created_at=row.created_at,
    )


class TemplateManager:
    """Manages templates in SQLite.

    Seeds two default templates on first startup if the table is empty.
    """

    def __init__(
        self,
        session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
    ) -> None:
        self._session_factory = session_factory or _default_session_factory

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    async def seed_defaults(self) -> None:
        """Insert the Carousel and Painting templates if the table is empty."""
        async with self._session_factory() as session:
            result = await session.execute(select(TemplateDB.id))
            if result.first() is not None:
                logger.debug("Templates already seeded — skipping")
                return

        base_prompts = _load_default_prompts()

        # --- Carousel template ---
        carousel_prompts = dict(base_prompts)
        carousel_prompts.update(_CAROUSEL_PROMPTS)
        carousel_config = ProjectConfig(
            global_defaults=GlobalDefaultsConfig(
                num_slides=None,
                include_titles=True,
                words_per_slide="ai",
            ),
            style=StyleConfig(default_text_enabled=True),
            prompts=carousel_prompts,
        )

        # --- Painting template ---
        painting_prompts = dict(base_prompts)
        painting_prompts.update(_PAINTING_PROMPTS)
        painting_config = ProjectConfig(
            global_defaults=GlobalDefaultsConfig(
                num_slides=1,
                include_titles=False,
                words_per_slide="keep_as_is",
            ),
            style=StyleConfig(default_text_enabled=False),
            prompts=painting_prompts,
        )

        templates = [
            ("Carousel", 5, carousel_config),
            ("Painting", 1, painting_config),
        ]

        async with self._session_factory() as session:
            async with session.begin():
                for name, slide_count, config in templates:
                    row = TemplateDB(
                        id=str(uuid.uuid4()),
                        name=name,
                        default_slide_count=slide_count,
                        config=config.model_dump(mode="json"),
                        created_at=datetime.utcnow(),
                    )
                    session.add(row)

        logger.info("Seeded default templates: Carousel, Painting")

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def list_templates(self) -> List[TemplateData]:
        """Return all templates."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(TemplateDB).order_by(TemplateDB.name)
            )
            rows = result.scalars().all()
        return [_row_to_data(row) for row in rows]

    async def get_template(self, template_id: str) -> Optional[TemplateData]:
        """Return a template by ID, or None."""
        async with self._session_factory() as session:
            row = await session.get(TemplateDB, template_id)
        return _row_to_data(row) if row else None

    async def get_template_config(
        self, template_id: str
    ) -> Optional[ProjectConfig]:
        """Return just the ProjectConfig for a given template."""
        tmpl = await self.get_template(template_id)
        return tmpl.config if tmpl else None

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def create_template(
        self,
        name: str,
        default_slide_count: int = 5,
        config: Optional[ProjectConfig] = None,
    ) -> TemplateData:
        """Create a new template."""
        if config is None:
            prompts = _load_default_prompts()
            config = ProjectConfig(prompts=prompts)

        row = TemplateDB(
            id=str(uuid.uuid4()),
            name=name,
            default_slide_count=default_slide_count,
            config=config.model_dump(mode="json"),
            created_at=datetime.utcnow(),
        )
        async with self._session_factory() as session:
            async with session.begin():
                session.add(row)

        return _row_to_data(row)

    async def update_template(
        self,
        template_id: str,
        name: Optional[str] = None,
        default_slide_count: Optional[int] = None,
        config: Optional[ProjectConfig] = None,
    ) -> Optional[TemplateData]:
        """Update mutable fields on an existing template."""
        async with self._session_factory() as session:
            async with session.begin():
                row = await session.get(TemplateDB, template_id)
                if row is None:
                    return None
                if name is not None:
                    row.name = name
                if default_slide_count is not None:
                    row.default_slide_count = default_slide_count
                if config is not None:
                    row.config = config.model_dump(mode="json")
        return await self.get_template(template_id)

    async def delete_template(self, template_id: str) -> bool:
        """Delete a template. Returns True if it existed."""
        async with self._session_factory() as session:
            async with session.begin():
                row = await session.get(TemplateDB, template_id)
                if row is None:
                    return False
                await session.delete(row)
        return True

    async def _clear_all(self) -> None:
        """Wipe all templates from the DB.  Used in tests."""
        async with self._session_factory() as session:
            async with session.begin():
                await session.execute(delete(TemplateDB))


# Module-level singleton
template_manager = TemplateManager()
