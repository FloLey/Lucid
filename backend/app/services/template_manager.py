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

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default templates seeded on first boot
# ---------------------------------------------------------------------------

_DEFAULT_TEMPLATES = [
    {
        "name": "Default (5 slides)",
        "default_slide_count": 5,
    },
    {
        "name": "Single Image (1 slide)",
        "default_slide_count": 1,
    },
]


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
        default_mode=row.default_mode,
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
        """Insert the two default templates if the templates table is empty."""
        async with self._session_factory() as session:
            result = await session.execute(select(TemplateDB.id))
            if result.first() is not None:
                logger.debug("Templates already seeded — skipping")
                return

        prompts = _load_default_prompts()
        base_config = ProjectConfig(prompts=prompts)

        async with self._session_factory() as session:
            async with session.begin():
                for tmpl in _DEFAULT_TEMPLATES:
                    row = TemplateDB(
                        id=str(uuid.uuid4()),
                        name=tmpl["name"],
                        default_mode="carousel",
                        default_slide_count=tmpl["default_slide_count"],
                        config=base_config.model_dump(mode="json"),
                        created_at=datetime.utcnow(),
                    )
                    session.add(row)

        logger.info("Seeded default templates")

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
            default_mode="carousel",
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
