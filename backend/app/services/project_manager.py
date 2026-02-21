"""Project management service backed by SQLite via SQLAlchemy async."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.database import async_session_factory as _default_session_factory
from app.db.models import ProjectDB
from app.models.project import (
    MAX_STAGES,
    ProjectCard,
    ProjectConfig,
    ProjectState,
)

if TYPE_CHECKING:
    from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)


def _state_to_db_row(project: ProjectState) -> dict:
    """Serialise a ProjectState into DB column values."""
    project.update_timestamp()
    state_blob = project.model_dump(
        mode="json",
        exclude={
            "project_id",
            "name",
            "slide_count",
            "current_stage",
            "project_config",
            "thumbnail_url",
            "created_at",
            "updated_at",
        },
    )
    return {
        "id": project.project_id,
        "name": project.name,
        "slide_count": project.slide_count,
        "current_stage": project.current_stage,
        "project_config": project.project_config.model_dump(mode="json"),
        "state": state_blob,
        # DB column is still named thumbnail_b64 to avoid a migration
        "thumbnail_b64": project.thumbnail_url,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }


def _db_row_to_state(row: ProjectDB) -> ProjectState:
    """Reconstruct a ProjectState from a DB row."""
    state_data: dict = dict(row.state) if row.state else {}
    state_data.update(
        {
            "project_id": row.id,
            "name": row.name,
            "slide_count": row.slide_count,
            "current_stage": row.current_stage,
            "project_config": row.project_config,
            # DB column is still named thumbnail_b64; map to the renamed Pydantic field
            "thumbnail_url": row.thumbnail_b64,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
    )
    return ProjectState.model_validate(state_data)


class ProjectManager:
    """Manages project state with SQLite as the sole source of truth.

    All mutation methods are async. SQLite is used directly for all reads
    and writes — no in-memory cache is maintained so memory usage stays
    flat regardless of how many projects or how large their image payloads.
    """

    def __init__(
        self,
        session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
    ) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = (
            session_factory or _default_session_factory
        )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_project(
        self,
        slide_count: int = 5,
        project_config: Optional[ProjectConfig] = None,
        name: Optional[str] = None,
    ) -> ProjectState:
        """Create a new project and persist it to the DB."""
        project_id = str(uuid.uuid4())
        short_id = project_id[:6]
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        auto_name = name or f"Untitled • {today} • {short_id}"

        project = ProjectState(
            project_id=project_id,
            name=auto_name,
            slide_count=slide_count,
            project_config=project_config or ProjectConfig(),
            current_stage=1,
        )

        await self._save_to_db(project)
        logger.info(f"Created project {project_id} ({auto_name})")
        return project

    async def get_project(self, project_id: str) -> Optional[ProjectState]:
        """Fetch a project directly from the DB."""
        async with self._session_factory() as session:
            row = await session.get(ProjectDB, project_id)
        if row is None:
            return None
        return _db_row_to_state(row)

    async def update_project(self, project: ProjectState) -> ProjectState:
        """Persist changes to *project* directly to the DB."""
        await self._save_to_db(project)
        return project

    async def delete_project(
        self,
        project_id: str,
        storage_service: Optional[StorageService] = None,
    ) -> bool:
        """Remove a project from the DB. Returns True if it existed.

        If *storage_service* is provided, all image files associated with the
        project's slides are deleted from disk before the DB row is removed.
        """
        if storage_service:
            project = await self.get_project(project_id)
            if project:
                for slide in project.slides:
                    storage_service.delete_image(slide.background_image_url)
                    storage_service.delete_image(slide.final_image_url)

        async with self._session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    delete(ProjectDB).where(ProjectDB.id == project_id)
                )
                return result.rowcount > 0

    async def list_projects(self) -> List[ProjectCard]:
        """Return lightweight cards for all projects, sorted newest-first."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(
                    ProjectDB.id,
                    ProjectDB.name,
                    ProjectDB.current_stage,
                    ProjectDB.slide_count,
                    ProjectDB.thumbnail_b64,
                    ProjectDB.created_at,
                    ProjectDB.updated_at,
                ).order_by(ProjectDB.updated_at.desc())
            )
            rows = result.all()

        return [
            ProjectCard(
                project_id=row.id,
                name=row.name,
                current_stage=row.current_stage,
                slide_count=row.slide_count,
                thumbnail_url=row.thumbnail_b64,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

    async def rename_project(
        self, project_id: str, name: str
    ) -> Optional[ProjectState]:
        """Update the project name."""
        project = await self.get_project(project_id)
        if not project:
            return None
        project.name = name
        return await self.update_project(project)

    # ------------------------------------------------------------------
    # Stage navigation
    # ------------------------------------------------------------------

    async def advance_stage(self, project_id: str) -> Optional[ProjectState]:
        """Advance to the next stage (max MAX_STAGES)."""
        project = await self.get_project(project_id)
        if not project:
            return None
        if project.current_stage < MAX_STAGES:
            project.current_stage += 1
            await self.update_project(project)
        return project

    async def previous_stage(self, project_id: str) -> Optional[ProjectState]:
        """Return to the previous stage (min 1)."""
        project = await self.get_project(project_id)
        if not project:
            return None
        if project.current_stage > 1:
            project.current_stage -= 1
            await self.update_project(project)
        return project

    async def go_to_stage(
        self, project_id: str, stage: int
    ) -> Optional[ProjectState]:
        """Jump to a specific stage (1–MAX_STAGES)."""
        project = await self.get_project(project_id)
        if not project:
            return None
        if 1 <= stage <= MAX_STAGES:
            project.current_stage = stage
            await self.update_project(project)
        return project

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    def clear_all(self) -> None:
        """Wipe all projects from the DB.  Used in tests."""
        import asyncio

        asyncio.run(self._async_clear_db())

    async def _async_clear_db(self) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                await session.execute(delete(ProjectDB))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _save_to_db(self, project: ProjectState) -> None:
        """Upsert a project row (INSERT OR REPLACE)."""
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        row = _state_to_db_row(project)
        async with self._session_factory() as session:
            async with session.begin():
                stmt = sqlite_insert(ProjectDB).values(**row)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["id"],
                    set_={k: v for k, v in row.items() if k != "id"},
                )
                await session.execute(stmt)


# Module-level singleton — used by the DI container
project_manager = ProjectManager()
