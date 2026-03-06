"""Matrix generation orchestrator and SSE event-queue manager.

Responsibilities:
- Start/cancel per-project asyncio generation tasks
- Manage per-project SSE event queues (fan-out to multiple subscribers)
- Persist each partial result to DB via MatrixDB
- Broadcast events to all connected SSE clients
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from app.models.matrix import CreateMatrixRequest, MatrixProject, MatrixSettings
from app.services.async_utils import bounded_gather
from app.services.gemini_service import GeminiError
from app.services.matrix_db import MatrixDB
from app.services.matrix_generator import MatrixGenerator

logger = logging.getLogger(__name__)

# Module-level state ── one entry per actively-generating project
_tasks: Dict[str, "asyncio.Task[None]"] = {}
_queues: Dict[str, List[asyncio.Queue]] = {}  # fan-out: multiple SSE clients


class MatrixService:
    """Orchestrates matrix generation and SSE event routing."""

    def __init__(
        self,
        matrix_db: MatrixDB,
        matrix_generator: MatrixGenerator,
        settings: Optional[MatrixSettings] = None,
    ) -> None:
        self._db = matrix_db
        self._gen = matrix_generator
        self._settings = settings or MatrixSettings()

    def load_settings(self, settings: MatrixSettings) -> None:
        self._settings = settings

    # ── Public: project lifecycle ─────────────────────────────────────────

    async def create_and_start(self, req: CreateMatrixRequest) -> MatrixProject:
        """Create DB row + cell stubs, start background generation, return immediately."""
        effective_theme = (
            req.description if req.input_mode == "description" else req.theme
        )
        project = await self._db.create_project(
            theme=effective_theme or "",
            n=req.n,
            language=req.language,
            style_mode=req.style_mode,
            include_images=req.include_images,
            name=req.name,
            input_mode=req.input_mode,
            description=req.description,
            n_rows=req.effective_n_rows if req.input_mode == "description" else 0,
            n_cols=req.effective_n_cols if req.input_mode == "description" else 0,
        )
        await self._db.update_project_status(project.id, "generating")
        _queues[project.id] = []

        task = asyncio.create_task(
            self._run_pipeline(project.id, req),
            name=f"matrix-{project.id[:8]}",
        )
        _tasks[project.id] = task
        task.add_done_callback(lambda _t: _tasks.pop(project.id, None))
        # Re-fetch so the returned project reflects status="generating", not "pending".
        # The frontend only auto-starts the SSE stream when status=="generating".
        updated = await self._db.get_project(project.id)
        return updated or project

    def is_generating(self, project_id: str) -> bool:
        return project_id in _tasks

    async def cancel_generation(self, project_id: str) -> None:
        task = _tasks.pop(project_id, None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        await self._db.update_project_status(
            project_id, "failed", "Cancelled by user"
        )

    async def generate_images_for_project(self, project_id: str) -> None:
        """Trigger image generation for all cells of an existing complete project."""
        project = await self._db.get_project(project_id)
        if project is None:
            raise ValueError("Project not found")
        _queues.setdefault(project_id, [])

        async def _gen_one(row: int, col: int, concept: str, context: str) -> None:
            try:
                image_url = await self._gen.generate_cell_image(
                    project_id=project_id,
                    row=row,
                    col=col,
                    concept=concept,
                    context=context,
                    settings=self._settings,
                    emit=self._emit,
                )
                await self._db.upsert_cell(
                    project_id, row, col, image_url=image_url
                )
            except Exception as exc:
                logger.warning("Image gen failed for (%d,%d): %s", row, col, exc)

        coros = []
        for cell in project.cells:
            concept = cell.label if cell.row == cell.col else cell.concept
            context = cell.definition if cell.row == cell.col else cell.explanation
            if concept:
                coros.append(_gen_one(cell.row, cell.col, concept or "", context or ""))

        await bounded_gather(coros, limit=min(self._settings.max_concurrency, 4))

    async def regenerate_cell(
        self,
        project_id: str,
        row: int,
        col: int,
        extra_instructions: str = "",
        image_only: bool = False,
    ) -> None:
        """Regenerate a single off-diagonal cell (or its image only)."""
        project = await self._db.get_project(project_id)
        if project is None:
            raise ValueError("Project not found")

        if project.input_mode == "description":
            # Description mode: use project-level row/col labels
            row_concept = {
                "label": project.row_labels[row] if row < len(project.row_labels) else f"Row {row}",
                "definition": "",
            }
            col_concept = {
                "label": project.col_labels[col] if col < len(project.col_labels) else f"Col {col}",
                "definition": "",
            }
            # Descriptors are stored per-cell for description mode (set during pipeline)
            cell_obj = await self._db.get_cell(project_id, row, col)
            row_descriptor = cell_obj.row_descriptor or row_concept["label"] if cell_obj else row_concept["label"]
            col_descriptor = cell_obj.col_descriptor or col_concept["label"] if cell_obj else col_concept["label"]
        else:
            # Theme mode: use diagonal cells
            diag_cells = {
                c.row: c for c in project.cells if c.row == c.col
            }
            row_concept = {
                "label": diag_cells[row].label or "",
                "definition": diag_cells[row].definition or "",
            }
            col_concept = {
                "label": diag_cells[col].label or "",
                "definition": diag_cells[col].definition or "",
            }
            row_descriptor = diag_cells[row].row_descriptor or ""
            col_descriptor = diag_cells[col].col_descriptor or ""

        if image_only:
            cell = await self._db.get_cell(project_id, row, col)
            concept = cell.concept if cell else ""
            explanation = cell.explanation if cell else ""
            context = f"{row_concept['label']} meets {col_concept['label']}"
            _queues.setdefault(project_id, [])
            image_url = await self._gen.generate_cell_image(
                project_id, row, col,
                concept or "", context,
                self._settings, self._emit,
            )
            await self._db.upsert_cell(project_id, row, col, image_url=image_url)
            return

        # Collect already-used labels to avoid duplicates
        all_cells = await self._db.get_all_cells(project_id)
        used_labels = [
            c.concept for c in all_cells
            if c.concept and not (c.row == row and c.col == col)
        ]

        _queues.setdefault(project_id, [])
        await self._db.upsert_cell(project_id, row, col, cell_status="generating")
        result = await self._gen.generate_cell(
            project_id=project_id,
            row=row,
            col=col,
            row_concept=row_concept,
            col_concept=col_concept,
            row_descriptor=row_descriptor,
            col_descriptor=col_descriptor,
            already_used_labels=used_labels,
            theme=project.theme,
            style_mode=project.style_mode,
            settings=self._settings,
            emit=self._emit,
            extra_instructions=extra_instructions,
        )
        await self._db.upsert_cell(
            project_id, row, col,
            concept=result["concept"],
            explanation=result["explanation"],
            cell_status="complete",
        )

    # ── SSE subscription ──────────────────────────────────────────────────

    async def subscribe(self, project_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Yield SSE events for a project until generation completes.
        Late subscribers (project already done) receive a snapshot + done immediately.
        """
        project = await self._db.get_project(project_id)
        if project is None:
            yield {"type": "error", "project_id": project_id, "message": "Not found"}
            return

        if project.status in ("complete", "failed"):
            yield {
                "type": "snapshot",
                "project_id": project_id,
                "matrix": project.model_dump(mode="json"),
            }
            terminal_event: Dict[str, Any] = {
                "type": "done" if project.status == "complete" else "error",
                "project_id": project_id,
            }
            if project.status == "failed":
                terminal_event["message"] = project.error_message or "Generation failed"
            yield terminal_event
            return

        # Create a personal queue and register it
        sub_q: asyncio.Queue = asyncio.Queue(maxsize=1024)
        _queues.setdefault(project_id, []).append(sub_q)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(sub_q.get(), timeout=30.0)
                    yield event
                    if event.get("type") in ("done", "error"):
                        break
                except asyncio.TimeoutError:
                    yield {"type": "heartbeat", "project_id": project_id}
        finally:
            try:
                _queues.get(project_id, []).remove(sub_q)
            except ValueError:
                pass

    # ── Background pipeline ───────────────────────────────────────────────

    async def _run_pipeline(
        self, project_id: str, req: CreateMatrixRequest
    ) -> None:
        """Full generation pipeline running as a background asyncio.Task."""
        settings = self._settings
        n = req.n
        # In description mode, req.theme is empty; the description itself acts as theme.
        theme = req.description if req.input_mode == "description" else req.theme
        style_mode = req.style_mode

        try:
            # Steps 1 + 2 — Fork based on input mode
            if req.input_mode == "description":
                n_rows = req.effective_n_rows
                n_cols = req.effective_n_cols
                # Single LLM call derives separate row/col labels and axis descriptors
                row_concepts, col_concepts, row_axes, col_axes = (
                    await self._gen.generate_from_description(
                        project_id=project_id,
                        description=req.description or "",
                        n_rows=n_rows,
                        n_cols=n_cols,
                        language=req.language,
                        style_mode=style_mode,
                        settings=settings,
                        emit=self._emit,
                    )
                )
                # Persist row/col labels on the project for display
                await self._db.update_project_labels(
                    project_id,
                    [c["label"] for c in row_concepts],
                    [c["label"] for c in col_concepts],
                )
            else:
                n_rows = n
                n_cols = n
                # Step 1 — Diagonal concepts
                concepts = await self._gen.generate_diagonal(
                    project_id=project_id,
                    theme=theme,
                    n=n,
                    language=req.language,
                    style_mode=style_mode,
                    settings=settings,
                    emit=self._emit,
                )
                # Persist diagonal cells
                for i, c in enumerate(concepts):
                    await self._db.upsert_cell(
                        project_id, i, i,
                        label=c["label"],
                        definition=c["definition"],
                        cell_status="complete",
                    )

                # Step 2 — Axes (parallel)
                axes_results: List[Tuple[str, str]] = await bounded_gather(
                    [
                        self._gen.generate_axes_for_concept(
                            project_id=project_id,
                            diagonal_index=i,
                            concept=concepts[i],
                            all_concepts=concepts,
                            settings=settings,
                            emit=self._emit,
                        )
                        for i in range(n)
                    ],
                    limit=settings.max_concurrency,
                )
                for i, (row_desc, col_desc) in enumerate(axes_results):
                    await self._db.upsert_cell(
                        project_id, i, i,
                        row_descriptor=row_desc,
                        col_descriptor=col_desc,
                    )

            # Step 3 — Cell generation.
            # Description mode: all n_rows × n_cols cells generated equally.
            # Theme mode: only off-diagonal cells (diagonal pre-populated in steps 1+2).
            if req.input_mode == "description":
                cells_to_generate = [
                    (r, c) for r in range(n_rows) for c in range(n_cols)
                ]
            else:
                cells_to_generate = sorted(
                    [(r, c) for r in range(n) for c in range(n) if r != c],
                    key=lambda rc: (abs(rc[0] - rc[1]), rc[0], rc[1]),
                )

            # Collect all labels to avoid duplicates across cells.
            # A lock ensures concurrent coroutines take consistent snapshots.
            if req.input_mode == "description":
                all_labels = [c["label"] for c in row_concepts] + [c["label"] for c in col_concepts]
            else:
                all_labels = [c["label"] for c in concepts]
            used_labels: List[str] = list(all_labels)
            labels_lock = asyncio.Lock()

            async def _gen_one_cell(row: int, col: int) -> None:
                if req.input_mode == "description":
                    row_concept = row_concepts[row]
                    col_concept = col_concepts[col]
                    row_descriptor = row_axes[row]
                    col_descriptor = col_axes[col]
                else:
                    row_concept = concepts[row]
                    col_concept = concepts[col]
                    row_descriptor = axes_results[row][0]
                    col_descriptor = axes_results[col][1]

                await self._db.upsert_cell(
                    project_id, row, col,
                    row_descriptor=row_descriptor,
                    col_descriptor=col_descriptor,
                    cell_status="generating",
                )
                try:
                    async with labels_lock:
                        snapshot = list(used_labels)
                    result = await self._gen.generate_cell(
                        project_id=project_id,
                        row=row,
                        col=col,
                        row_concept=row_concept,
                        col_concept=col_concept,
                        row_descriptor=row_descriptor,
                        col_descriptor=col_descriptor,
                        already_used_labels=snapshot,
                        theme=theme,
                        style_mode=style_mode,
                        settings=settings,
                        emit=self._emit,
                    )
                    async with labels_lock:
                        used_labels.append(result["concept"])
                    await self._db.upsert_cell(
                        project_id, row, col,
                        concept=result["concept"],
                        explanation=result["explanation"],
                        cell_status="complete",
                    )
                    completed = sum(1 for lbl in used_labels if lbl not in all_labels)
                    await self._emit(
                        {
                            "type": "progress",
                            "project_id": project_id,
                            "generated": completed,
                            "total": len(cells_to_generate),
                        }
                    )
                except Exception as exc:
                    logger.warning("Cell (%d,%d) failed: %s", row, col, exc)
                    await self._db.upsert_cell(
                        project_id, row, col,
                        cell_status="failed",
                        cell_error=str(exc),
                    )
                    await self._emit(
                        {
                            "type": "cell_failed",
                            "project_id": project_id,
                            "row": row,
                            "col": col,
                            "error": str(exc),
                        }
                    )

            await bounded_gather(
                [_gen_one_cell(r, c) for r, c in cells_to_generate],
                limit=settings.max_concurrency,
            )

            # Step 4 — Validate + targeted retry
            for attempt in range(settings.max_retries + 1):
                all_cells = await self._db.get_all_cells(project_id)
                cells_grid = _build_grid(all_cells, n_rows, n_cols)
                if req.input_mode == "description":
                    failures = await self._gen.validate_matrix(
                        project_id=project_id,
                        theme=theme,
                        cells_grid=cells_grid,
                        settings=settings,
                        emit=self._emit,
                        row_axes=row_axes,
                        col_axes=col_axes,
                    )
                else:
                    failures = await self._gen.validate_matrix(
                        project_id=project_id,
                        theme=theme,
                        cells_grid=cells_grid,
                        settings=settings,
                        emit=self._emit,
                        axes=axes_results,
                    )
                if not failures:
                    break
                if attempt < settings.max_retries:
                    logger.info(
                        "Matrix %s: retrying %d cells (attempt %d)",
                        project_id[:8], len(failures), attempt + 1,
                    )
                    await MatrixGenerator._backoff(attempt)
                    await bounded_gather(
                        [_gen_one_cell(r, c) for r, c in failures],
                        limit=settings.max_concurrency,
                    )

            # Step 5 — Images (optional)
            if req.include_images:
                all_cells = await self._db.get_all_cells(project_id)

                async def _img(cell_row: int, cell_col: int) -> None:
                    cell = await self._db.get_cell(project_id, cell_row, cell_col)
                    if cell is None:
                        return
                    concept = cell.concept or ""
                    context: str
                    if req.input_mode == "description":
                        row_lbl = row_concepts[cell_row]["label"] if cell_row < len(row_concepts) else ""
                        col_lbl = col_concepts[cell_col]["label"] if cell_col < len(col_concepts) else ""
                        context = f"{row_lbl} meets {col_lbl}"
                    elif cell_row == cell_col:
                        concept = cell.label or ""
                        context = cell.definition or ""
                    else:
                        concept = cell.concept or ""
                        context = (
                            f"{concepts[cell_row].get('label', '')} meets "
                            f"{concepts[cell_col].get('label', '')}"
                        )
                    if not concept:
                        return
                    try:
                        image_url = await self._gen.generate_cell_image(
                            project_id, cell_row, cell_col,
                            concept, context, settings, self._emit,
                        )
                        await self._db.upsert_cell(
                            project_id, cell_row, cell_col, image_url=image_url
                        )
                    except Exception as exc:
                        logger.warning(
                            "Image failed (%d,%d): %s", cell_row, cell_col, exc
                        )

                await bounded_gather(
                    [_img(c.row, c.col) for c in all_cells],
                    limit=min(settings.max_concurrency, 4),
                )

            # Done
            await self._db.update_project_status(project_id, "complete")
            await self._emit({"type": "done", "project_id": project_id})

        except asyncio.CancelledError:
            raise
        except GeminiError as exc:
            logger.error("Matrix %s GeminiError: %s", project_id[:8], exc)
            await self._db.update_project_status(project_id, "failed", str(exc))
            await self._emit(
                {"type": "error", "project_id": project_id, "message": str(exc)}
            )
        except Exception as exc:
            logger.exception("Matrix %s unexpected error", project_id[:8])
            await self._db.update_project_status(project_id, "failed", str(exc))
            await self._emit(
                {"type": "error", "project_id": project_id, "message": str(exc)}
            )
        finally:
            # Small delay so clients can receive the final event before cleanup
            await asyncio.sleep(2)
            _queues.pop(project_id, None)

    # ── Event broadcasting ────────────────────────────────────────────────

    async def _emit(self, event: Dict[str, Any]) -> None:
        """Push event to all subscriber queues for the project."""
        project_id = event.get("project_id", "")
        for q in list(_queues.get(project_id, [])):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                logger.debug("SSE queue full for %s, dropping event", project_id[:8])


# ── Helpers ───────────────────────────────────────────────────────────────


def _build_grid(
    cells: List[Any], n_rows: int, n_cols: int
) -> List[List[Dict[str, str]]]:
    """Build n_rows×n_cols grid of cell dicts for the validator prompt."""
    grid: List[List[Dict[str, str]]] = [[{} for _ in range(n_cols)] for _ in range(n_rows)]
    for cell in cells:
        r, c = cell.row, cell.col
        if 0 <= r < n_rows and 0 <= c < n_cols:
            grid[r][c] = {
                "concept": cell.concept or cell.label or "",
                "explanation": cell.explanation or cell.definition or "",
            }
    return grid
