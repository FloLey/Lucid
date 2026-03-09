"""SQLite CRUD layer for the Concept Matrix Generator."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import delete, select, text, update
from sqlalchemy.dialects.sqlite import insert as sqlite_upsert

from app.db.database import async_session_factory, engine
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
    row_labels: List[str] = json.loads(row.row_labels_json) if row.row_labels_json else []
    col_labels: List[str] = json.loads(row.col_labels_json) if row.col_labels_json else []
    return MatrixProject(
        id=row.id,
        name=row.name,
        theme=row.theme,
        n=row.n,
        n_rows=row.n_rows or 0,
        n_cols=row.n_cols or 0,
        row_labels=row_labels,
        col_labels=col_labels,
        row_axis_title=row.row_axis_title,
        col_axis_title=row.col_axis_title,
        language=row.language,
        style_mode=row.style_mode,
        include_images=bool(row.include_images),
        input_mode=row.input_mode,
        description=row.description,
        status=row.status,
        error_message=row.error_message,
        cells=cells,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


# ── Service ───────────────────────────────────────────────────────────────


class MatrixDB:
    """CRUD operations for matrix_projects and matrix_cells tables."""

    # ── Schema migration ──────────────────────────────────────────────────

    @staticmethod
    async def run_migrations() -> None:
        """Add new columns to existing tables (idempotent, SQLite ALTER TABLE)."""
        new_columns = [
            "ALTER TABLE matrix_projects ADD COLUMN input_mode TEXT DEFAULT 'theme'",
            "ALTER TABLE matrix_projects ADD COLUMN description TEXT",
            "ALTER TABLE matrix_projects ADD COLUMN n_rows INTEGER",
            "ALTER TABLE matrix_projects ADD COLUMN n_cols INTEGER",
            "ALTER TABLE matrix_projects ADD COLUMN row_labels_json TEXT",
            "ALTER TABLE matrix_projects ADD COLUMN col_labels_json TEXT",
            "ALTER TABLE matrix_projects ADD COLUMN row_axis_title TEXT",
            "ALTER TABLE matrix_projects ADD COLUMN col_axis_title TEXT",
        ]
        for col_sql in new_columns:
            try:
                async with engine.begin() as conn:
                    await conn.execute(text(col_sql))
            except Exception as exc:
                if "duplicate column" in str(exc).lower():
                    logger.debug("Migration: column already exists, skipping (%s)", exc)
                else:
                    logger.warning("Unexpected error during DB migration: %s — %s", col_sql, exc)

    # ── Projects ──────────────────────────────────────────────────────────

    async def create_project(
        self,
        theme: str,
        n: int,
        language: str,
        style_mode: str,
        include_images: bool,
        name: Optional[str] = None,
        input_mode: str = "theme",
        description: Optional[str] = None,
        n_rows: int = 0,
        n_cols: int = 0,
    ) -> MatrixProject:
        project_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        short = project_id[:6]
        auto_name = name or f"Matrix • {theme[:40]} • {short}"
        # Effective dimensions
        eff_rows = n_rows if n_rows > 0 else n
        eff_cols = n_cols if n_cols > 0 else n

        async with async_session_factory() as session:
            async with session.begin():
                row = MatrixProjectDB(
                    id=project_id,
                    name=auto_name,
                    theme=theme,
                    n=n,
                    n_rows=n_rows if n_rows > 0 else None,
                    n_cols=n_cols if n_cols > 0 else None,
                    language=language,
                    style_mode=style_mode,
                    include_images=int(include_images),
                    input_mode=input_mode,
                    description=description,
                    status="pending",
                    error_message=None,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)

        # Pre-create all cell stubs so grid renders immediately
        await self._create_cell_stubs(project_id, eff_rows, eff_cols)
        project = await self.get_project(project_id)
        if project is None:
            raise RuntimeError(f"Failed to fetch project {project_id} after creation")
        return project

    async def _create_cell_stubs(self, project_id: str, n_rows: int, n_cols: int) -> None:
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
            for r in range(n_rows)
            for c in range(n_cols)
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
                n_rows=r.n_rows or 0,
                n_cols=r.n_cols or 0,
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

    async def update_project_labels(
        self,
        project_id: str,
        row_labels: List[str],
        col_labels: List[str],
        row_axis_title: Optional[str] = None,
        col_axis_title: Optional[str] = None,
    ) -> None:
        """Store row/col axis labels and optional axis titles (description mode)."""
        now = datetime.now(timezone.utc)
        values: dict = dict(
            row_labels_json=json.dumps(row_labels),
            col_labels_json=json.dumps(col_labels),
            updated_at=now,
        )
        if row_axis_title is not None:
            values["row_axis_title"] = row_axis_title
        if col_axis_title is not None:
            values["col_axis_title"] = col_axis_title
        async with async_session_factory() as session:
            async with session.begin():
                await session.execute(
                    update(MatrixProjectDB)
                    .where(MatrixProjectDB.id == project_id)
                    .values(**values)
                )

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

    async def swap_cells(
        self,
        project_id: str,
        row_a: int,
        col_a: int,
        row_b: int,
        col_b: int,
    ) -> tuple[Optional[MatrixCell], Optional[MatrixCell]]:
        """Atomically swap concept/explanation of two cells in one transaction.

        Returns the updated (cell_a, cell_b) Pydantic objects, or (None, None)
        if either cell does not exist (no changes are made in that case).
        """
        now = datetime.now(timezone.utc)
        async with async_session_factory() as session:
            async with session.begin():
                res_a = await session.execute(
                    select(MatrixCellDB).where(
                        MatrixCellDB.project_id == project_id,
                        MatrixCellDB.row == row_a,
                        MatrixCellDB.col == col_a,
                    )
                )
                db_a = res_a.scalar_one_or_none()

                res_b = await session.execute(
                    select(MatrixCellDB).where(
                        MatrixCellDB.project_id == project_id,
                        MatrixCellDB.row == row_b,
                        MatrixCellDB.col == col_b,
                    )
                )
                db_b = res_b.scalar_one_or_none()

                if db_a is None or db_b is None:
                    return None, None

                # Swap in-place within the same transaction
                db_a.concept, db_b.concept = db_b.concept, db_a.concept
                db_a.explanation, db_b.explanation = db_b.explanation, db_a.explanation

                await session.execute(
                    update(MatrixProjectDB)
                    .where(MatrixProjectDB.id == project_id)
                    .values(updated_at=now)
                )

                # Flush so the ORM objects reflect final state before we snapshot
                await session.flush()
                cell_a = _row_to_cell(db_a)
                cell_b = _row_to_cell(db_b)

        return cell_a, cell_b

    async def clear_all(self) -> None:
        """Delete all matrix projects and cells. For tests only."""
        async with async_session_factory() as session:
            async with session.begin():
                await session.execute(delete(MatrixCellDB))
                await session.execute(delete(MatrixProjectDB))
