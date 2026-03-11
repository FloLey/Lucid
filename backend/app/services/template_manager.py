"""Template management service — CRUD + default seeding."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.database import async_session_factory as _default_session_factory
from app.db.models import TemplateDB
from app.models.project import ProjectConfig, TemplateData
from app.models.config import GlobalDefaultsConfig, StyleConfig

logger = logging.getLogger(__name__)




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
        self._prompts_cache: Optional[Dict[str, Dict[str, str]]] = None

    def _load_template_prompts(self) -> Dict[str, Dict[str, str]]:
        """Return per-template prompt dicts, cached on this instance.

        Returns a mapping of ``{template_name: {prompt_name: content}}``.
        The result is cached so repeated calls (e.g. every ``create_template``
        API call) avoid redundant disk I/O.
        """
        if self._prompts_cache is None:
            from app.services.prompt_loader import PromptLoader, TEMPLATE_PROMPT_FILES

            loader = PromptLoader()
            self._prompts_cache = {
                name: loader.load_for_template(name)
                for name in TEMPLATE_PROMPT_FILES
            }
            # Include a generic fallback (no overrides) for custom templates
            self._prompts_cache[""] = loader.load_all()
        return self._prompts_cache

    def clear_cache(self) -> None:
        """Clear the prompt cache, forcing a reload on next access."""
        self._prompts_cache = None

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

        all_prompts = self._load_template_prompts()

        templates = [
            (
                "Carousel",
                5,
                ProjectConfig(
                    global_defaults=GlobalDefaultsConfig(
                        num_slides=None,
                        include_titles=True,
                        words_per_slide="ai",
                    ),
                    style=StyleConfig(default_text_enabled=True),
                    prompts=all_prompts["Carousel"],
                ),
            ),
            (
                "Painting",
                1,
                ProjectConfig(
                    global_defaults=GlobalDefaultsConfig(
                        num_slides=1,
                        include_titles=False,
                        words_per_slide="keep_as_is",
                    ),
                    style=StyleConfig(default_text_enabled=False),
                    prompts=all_prompts["Painting"],
                ),
            ),
        ]

        async with self._session_factory() as session:
            async with session.begin():
                for name, slide_count, config in templates:
                    row = TemplateDB(
                        id=str(uuid.uuid4()),
                        name=name,
                        default_slide_count=slide_count,
                        config=config.model_dump(mode="json"),
                        created_at=datetime.now(timezone.utc),
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
            prompts = self._load_template_prompts().get("") or {}
            config = ProjectConfig(prompts=prompts)

        row = TemplateDB(
            id=str(uuid.uuid4()),
            name=name,
            default_slide_count=default_slide_count,
            config=config.model_dump(mode="json"),
            created_at=datetime.now(timezone.utc),
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
