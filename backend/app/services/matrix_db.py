"""SQLite CRUD layer for the Concept Matrix Generator."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_upsert

from app.db.database import async_session_factory
from app.db.models import MatrixCellDB, MatrixProjectDB
from app.models.matrix import MatrixCell, MatrixProject, MatrixProjectCard

logger = logging.getLogger(__name__)


# ── Row → Pydantic helpers ────────────────────────────────────────────────


def _row_to_cell(row: MatrixCellDB) -> MatrixCell:
    return MatrixCell(
        id=row.id,
        project_id=row.project_id,
        row=row.row,
        col=row.col,
        label=row.label,
        definition=row.definition,
        row_descriptor=row.row_descriptor,
        col_descriptor=row.col_descriptor,
        concept=row.concept,
        explanation=row.explanation,
        image_url=row.image_url,
        cell_status=row.cell_status,
        cell_error=row.cell_error,
        attempts=row.attempts,
    )


def _row_to_project(row: MatrixProjectDB, cells: List[MatrixCell]) -> MatrixProject:
    return MatrixProject(
        id=row.id,
        name=row.name,
        theme=row.theme,
        n=row.n,
        language=row.language,
        style_mode=row.style_mode,
        include_images=bool(row.include_images),
        status=row.status,
        error_message=row.error_message,
        cells=cells,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


# ── Service ───────────────────────────────────────────────────────────────


class MatrixDB:
    """CRUD operations for matrix_projects and matrix_cells tables."""

    # ── Projects ──────────────────────────────────────────────────────────

    async def create_project(
        self,
        theme: str,
        n: int,
        language: str,
        style_mode: str,
        include_images: bool,
        name: Optional[str] = None,
    ) -> MatrixProject:
        project_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        short = project_id[:6]
        auto_name = name or f"Matrix • {theme[:40]} • {short}"

        async with async_session_factory() as session:
            async with session.begin():
                row = MatrixProjectDB(
                    id=project_id,
                    name=auto_name,
                    theme=theme,
                    n=n,
                    language=language,
                    style_mode=style_mode,
                    include_images=int(include_images),
                    status="pending",
                    error_message=None,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)

        # Pre-create all n*n cell stubs so grid renders immediately
        await self._create_cell_stubs(project_id, n)
        project = await self.get_project(project_id)
        if project is None:
            raise RuntimeError(f"Failed to fetch project {project_id} after creation")
        return project

    async def _create_cell_stubs(self, project_id: str, n: int) -> None:
        now = datetime.now(timezone.utc)
        cells = [
            {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "row": r,
                "col": c,
                "label": None,
                "definition": None,
                "row_descriptor": None,
                "col_descriptor": None,
                "concept": None,
                "explanation": None,
                "image_url": None,
                "cell_status": "pending",
                "cell_error": None,
                "attempts": 0,
            }
            for r in range(n)
            for c in range(n)
        ]
        async with async_session_factory() as session:
            async with session.begin():
                await session.execute(
                    sqlite_upsert(MatrixCellDB),
                    cells,
                )

    async def get_project(self, project_id: str) -> Optional[MatrixProject]:
        async with async_session_factory() as session:
            row = await session.get(MatrixProjectDB, project_id)
            if row is None:
                return None
            result = await session.execute(
                select(MatrixCellDB)
                .where(MatrixCellDB.project_id == project_id)
                .order_by(MatrixCellDB.row, MatrixCellDB.col)
            )
            cell_rows = result.scalars().all()
        return _row_to_project(row, [_row_to_cell(c) for c in cell_rows])

    async def list_projects(self) -> List[MatrixProjectCard]:
        async with async_session_factory() as session:
            result = await session.execute(
                select(MatrixProjectDB).order_by(MatrixProjectDB.updated_at.desc())
            )
            rows = result.scalars().all()
        return [
            MatrixProjectCard(
                id=r.id,
                name=r.name,
                theme=r.theme,
                n=r.n,
                status=r.status,
                include_images=bool(r.include_images),
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in rows
        ]

    async def delete_project(self, project_id: str) -> bool:
        async with async_session_factory() as session:
            async with session.begin():
                await session.execute(
                    delete(MatrixCellDB).where(
                        MatrixCellDB.project_id == project_id
                    )
                )
                result = await session.execute(
                    delete(MatrixProjectDB).where(
                        MatrixProjectDB.id == project_id
                    )
                )
                return result.rowcount > 0

    async def update_project_status(
        self,
        project_id: str,
        status: str,
        error_message: Optional[str] = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        async with async_session_factory() as session:
            async with session.begin():
                await session.execute(
                    update(MatrixProjectDB)
                    .where(MatrixProjectDB.id == project_id)
                    .values(
                        status=status,
                        error_message=error_message,
                        updated_at=now,
                    )
                )

    # ── Cells ─────────────────────────────────────────────────────────────

    async def upsert_cell(self, project_id: str, row: int, col: int, **fields: object) -> None:
        """Update fields on the pre-existing cell stub at (row, col)."""
        now = datetime.now(timezone.utc)
        async with async_session_factory() as session:
            async with session.begin():
                await session.execute(
                    update(MatrixCellDB)
                    .where(
                        MatrixCellDB.project_id == project_id,
                        MatrixCellDB.row == row,
                        MatrixCellDB.col == col,
                    )
                    .values(**fields)
                )
                # Touch project updated_at
                await session.execute(
                    update(MatrixProjectDB)
                    .where(MatrixProjectDB.id == project_id)
                    .values(updated_at=now)
                )

    async def get_cell(
        self, project_id: str, row: int, col: int
    ) -> Optional[MatrixCell]:
        async with async_session_factory() as session:
            result = await session.execute(
                select(MatrixCellDB).where(
                    MatrixCellDB.project_id == project_id,
                    MatrixCellDB.row == row,
                    MatrixCellDB.col == col,
                )
            )
            row_obj = result.scalar_one_or_none()
        return _row_to_cell(row_obj) if row_obj else None

    async def get_all_cells(self, project_id: str) -> List[MatrixCell]:
        async with async_session_factory() as session:
            result = await session.execute(
                select(MatrixCellDB)
                .where(MatrixCellDB.project_id == project_id)
                .order_by(MatrixCellDB.row, MatrixCellDB.col)
            )
            rows = result.scalars().all()
        return [_row_to_cell(r) for r in rows]

    async def clear_all(self) -> None:
        """Delete all matrix projects and cells. For tests only."""
        async with async_session_factory() as session:
            async with session.begin():
                await session.execute(delete(MatrixCellDB))
                await session.execute(delete(MatrixProjectDB))
