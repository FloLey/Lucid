"""Project management service backed by SQLite via SQLAlchemy async."""

from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.db.database import async_session_factory as _default_session_factory
from app.db.models import ProjectDB
from app.models.project import (
    ProjectCard,
    ProjectConfig,
    ProjectState,
)

logger = logging.getLogger(__name__)


def _state_to_db_row(project: ProjectState) -> dict:
    """Serialise a ProjectState into DB column values."""
    project.update_timestamp()
    state_blob = project.model_dump(
        mode="json",
        exclude={
            "project_id",
            "name",
            "mode",
            "slide_count",
            "current_stage",
            "project_config",
            "thumbnail_b64",
            "created_at",
            "updated_at",
        },
    )
    return {
        "id": project.project_id,
        "name": project.name,
        "mode": project.mode,
        "slide_count": project.slide_count,
        "current_stage": project.current_stage,
        "project_config": project.project_config.model_dump(mode="json"),
        "state": state_blob,
        "thumbnail_b64": project.thumbnail_b64,
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
            "mode": row.mode,
            "slide_count": row.slide_count,
            "current_stage": row.current_stage,
            "project_config": row.project_config,
            "thumbnail_b64": row.thumbnail_b64,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
    )
    return ProjectState.model_validate(state_data)


class ProjectManager:
    """Manages project state with SQLite persistence and in-memory cache.

    All mutation methods are async.  An in-memory dict provides fast reads
    while SQLite provides durability.
    """

    def __init__(
        self,
        session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
    ) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = (
            session_factory or _default_session_factory
        )
        self._cache: Dict[str, ProjectState] = {}
        self._global_lock = threading.Lock()
        self._project_locks: Dict[str, threading.Lock] = {}

    def _get_project_lock(self, project_id: str) -> threading.Lock:
        with self._global_lock:
            if project_id not in self._project_locks:
                self._project_locks[project_id] = threading.Lock()
            return self._project_locks[project_id]

    @asynccontextmanager
    async def _async_global_lock(self):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._global_lock.acquire)
        try:
            yield
        finally:
            self._global_lock.release()

    async def load_all(self) -> None:
        """Populate the in-memory cache from the DB (called at startup)."""
        async with self._session_factory() as session:
            result = await session.execute(select(ProjectDB))
            rows = result.scalars().all()
        for row in rows:
            try:
                project = _db_row_to_state(row)
                self._cache[project.project_id] = project
            except Exception as e:
                logger.warning(f"Failed to load project {row.id}: {e}")
        logger.info(f"Loaded {len(self._cache)} project(s) from DB")

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_project(
        self,
        mode: str = "carousel",
        slide_count: int = 5,
        project_config: Optional[ProjectConfig] = None,
        name: Optional[str] = None,
    ) -> ProjectState:
        """Create a new project and persist it to the DB."""
        project_id = str(uuid.uuid4())
        short_id = project_id[:6]
        today = datetime.utcnow().strftime("%Y-%m-%d")
        auto_name = name or f"Untitled • {today} • {short_id}"

        project = ProjectState(
            project_id=project_id,
            name=auto_name,
            mode=mode,
            slide_count=slide_count,
            project_config=project_config or ProjectConfig(),
            current_stage=1,
        )

        await self._save_to_db(project)
        async with self._async_global_lock():
            self._cache[project_id] = project

        logger.info(f"Created project {project_id} ({auto_name})")
        return project

    async def get_project(self, project_id: str) -> Optional[ProjectState]:
        """Return the cached project (or reload from DB if missing)."""
        async with self._async_global_lock():
            if project_id in self._cache:
                return self._cache[project_id]

        # Not in cache — try DB
        async with self._session_factory() as session:
            row = await session.get(ProjectDB, project_id)
        if row is None:
            return None

        project = _db_row_to_state(row)
        async with self._async_global_lock():
            self._cache[project_id] = project
        return project

    async def update_project(self, project: ProjectState) -> ProjectState:
        """Persist changes to *project* (cache + DB)."""
        project.update_timestamp()
        async with self._async_global_lock():
            self._cache[project.project_id] = project
        await self._save_to_db(project)
        return project

    async def delete_project(self, project_id: str) -> bool:
        """Remove a project from cache and DB. Returns True if it existed."""
        async with self._async_global_lock():
            existed = project_id in self._cache
            self._cache.pop(project_id, None)
            self._project_locks.pop(project_id, None)

        async with self._session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    delete(ProjectDB).where(ProjectDB.id == project_id)
                )
                deleted = result.rowcount > 0

        return existed or deleted

    async def list_projects(self) -> List[ProjectCard]:
        """Return lightweight cards for all projects, sorted newest-first."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(
                    ProjectDB.id,
                    ProjectDB.name,
                    ProjectDB.mode,
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
                mode=row.mode,
                current_stage=row.current_stage,
                slide_count=row.slide_count,
                thumbnail_b64=row.thumbnail_b64,
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
        """Advance to the next stage (max 5)."""
        project = await self.get_project(project_id)
        if not project:
            return None
        if project.current_stage < 5:
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
        """Jump to a specific stage (1–5)."""
        project = await self.get_project(project_id)
        if not project:
            return None
        if 1 <= stage <= 5:
            project.current_stage = stage
            await self.update_project(project)
        return project

    # ------------------------------------------------------------------
    # Context manager for per-project locking
    # ------------------------------------------------------------------

    @asynccontextmanager
    async def project_context(self, project_id: str):
        """Async context manager providing per-project lock."""
        lock = self._get_project_lock(project_id)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lock.acquire)
        try:
            yield await self.get_project(project_id)
        finally:
            lock.release()

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    def clear_all(self) -> None:
        """Wipe all projects from memory and DB.  Used in tests."""
        with self._global_lock:
            self._cache.clear()
            self._project_locks.clear()

        # Run a synchronous delete in a new event loop if needed
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self._async_clear_db())
            else:
                loop.run_until_complete(self._async_clear_db())
        except RuntimeError:
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
