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
        # Per-instance state: one entry per actively-generating project.
        # Protected by _lock to prevent races on concurrent requests for the same project.
        self._tasks: Dict[str, "asyncio.Task[None]"] = {}
        self._queues: Dict[str, List[asyncio.Queue]] = {}  # fan-out: multiple SSE clients
        self._lock = asyncio.Lock()

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
        async with self._lock:
            self._queues[project.id] = []
            task = asyncio.create_task(
                self._run_pipeline(project.id, req),
                name=f"matrix-{project.id[:8]}",
            )
            self._tasks[project.id] = task
        # Re-fetch so the returned project reflects status="generating", not "pending".
        # The frontend only auto-starts the SSE stream when status=="generating".
        updated = await self._db.get_project(project.id)
        return updated or project

    def is_generating(self, project_id: str) -> bool:
        return project_id in self._tasks

    async def cancel_generation(self, project_id: str) -> None:
        async with self._lock:
            task = self._tasks.pop(project_id, None)
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
        async with self._lock:
            self._queues.setdefault(project_id, [])

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
            if cell.row == cell.col and project.input_mode != "description":
                concept = cell.label
                context = cell.definition
            else:
                concept = cell.concept
                context = cell.explanation
            if concept:
                coros.append(_gen_one(cell.row, cell.col, concept or "", context or ""))

        await bounded_gather(coros, limit=min(self._settings.max_concurrency, 4))
        await self._db.update_project_status(project_id, "complete")
        await self._emit({"type": "done", "project_id": project_id})

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
            row_descriptor = (cell_obj.row_descriptor if cell_obj else None) or row_concept["label"]
            col_descriptor = (cell_obj.col_descriptor if cell_obj else None) or col_concept["label"]
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
            async with self._lock:
                self._queues.setdefault(project_id, [])
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

        async with self._lock:
            self._queues.setdefault(project_id, [])
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
        async with self._lock:
            self._queues.setdefault(project_id, []).append(sub_q)
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
                async with self._lock:
                    self._queues.get(project_id, []).remove(sub_q)
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
                row_concepts, col_concepts, row_axes, col_axes, _row_axis_title, _col_axis_title = (
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
                # Persist row/col labels and axis titles on the project for display
                _row_labels = [c["label"] for c in row_concepts]
                _col_labels = [c["label"] for c in col_concepts]
                await self._db.update_project_labels(
                    project_id,
                    _row_labels,
                    _col_labels,
                    row_axis_title=_row_axis_title,
                    col_axis_title=_col_axis_title,
                )
                # Broadcast labels immediately so live subscribers can render
                # column/row headers without waiting for the stream to complete.
                await self._emit(
                    {
                        "type": "labels",
                        "project_id": project_id,
                        "row_labels": _row_labels,
                        "col_labels": _col_labels,
                        "row_axis_title": _row_axis_title,
                        "col_axis_title": _col_axis_title,
                    }
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
            #
            # Generation order: corners first, centre last (decreasing Manhattan
            # distance from the grid centre).  Cells at the same distance form a
            # "ring" and are generated concurrently via bounded_gather so they
            # don't slow each other down; rings are processed one at a time so
            # each ring's cells see all concepts from prior (farther) rings in
            # already_used_labels, providing strong duplicate prevention across
            # the most conceptually similar positions while keeping parallelism.
            all_positions = [
                (r, c)
                for r in range(n_rows)
                for c in range(n_cols)
                if req.input_mode == "description" or r != c
            ]
            _cr, _cc = (n_rows - 1) / 2, (n_cols - 1) / 2

            def _dist(r: int, c: int) -> float:
                return abs(r - _cr) + abs(c - _cc)

            all_positions_sorted = sorted(
                all_positions,
                key=lambda rc: (-_dist(rc[0], rc[1]), rc[0] + rc[1], -rc[0]),
            )

            # Group into rings (consecutive positions with the same distance).
            rings: list[list[tuple[int, int]]] = []
            for pos in all_positions_sorted:
                if rings and _dist(*rings[-1][-1]) == _dist(*pos):
                    rings[-1].append(pos)
                else:
                    rings.append([pos])

            if req.input_mode == "description":
                all_labels = [c["label"] for c in row_concepts] + [c["label"] for c in col_concepts]
            else:
                all_labels = [c["label"] for c in concepts]
            used_labels: List[str] = list(all_labels)
            labels_lock = asyncio.Lock()

            async def _gen_one_cell(row: int, col: int, extra_instructions: str = "") -> None:
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
                        extra_instructions=extra_instructions,
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
                            "total": len(all_positions),
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

            for ring in rings:
                await bounded_gather(
                    [_gen_one_cell(r, c) for r, c in ring],
                    limit=settings.max_concurrency,
                )

            # Step 4 — Validate + targeted retry
            failures: List[Tuple[int, int, str]] = []
            swaps: List[Tuple[int, int, int, int]] = []
            for attempt in range(settings.max_retries + 1):
                all_cells = await self._db.get_all_cells(project_id)
                cells_grid = _build_grid(all_cells, n_rows, n_cols)
                if req.input_mode == "description":
                    failures, swaps = await self._gen.validate_matrix(
                        project_id=project_id,
                        theme=theme,
                        cells_grid=cells_grid,
                        settings=settings,
                        emit=self._emit,
                        row_axes=row_axes,
                        col_axes=col_axes,
                    )
                else:
                    failures, swaps = await self._gen.validate_matrix(
                        project_id=project_id,
                        theme=theme,
                        cells_grid=cells_grid,
                        settings=settings,
                        emit=self._emit,
                        axes=axes_results,
                    )
                if not failures and not swaps:
                    break
                if attempt < settings.max_retries:
                    logger.info(
                        "Matrix %s: swapping %d cell pair(s), retrying %d cell(s) (attempt %d)",
                        project_id[:8], len(swaps), len(failures), attempt + 1,
                    )
                    await MatrixGenerator._backoff(attempt)
                    # Apply swaps first — zero LLM calls, just repositions concepts
                    for ra, ca, rb, cb in swaps:
                        await self._apply_swap(project_id, ra, ca, rb, cb)
                    # Regenerate only the cells the validator flagged for regeneration.
                    # For duplicate pairs the validator only includes the weaker cell,
                    # so the better-placed duplicate is preserved untouched.
                    # Pass the failure reason as extra_instructions so the LLM knows
                    # why the previous attempt was rejected.
                    await bounded_gather(
                        [_gen_one_cell(r, c, reason) for r, c, reason in failures],
                        limit=settings.max_concurrency,
                    )

            # If validation failures remain after all retries, the frontend still
            # shows those cells as "generating" (from the last validation event).
            # Emit cell events to restore them to "complete" so the UI isn't stuck.
            if failures:
                for r, c, _ in failures:
                    cell = await self._db.get_cell(project_id, r, c)
                    if cell:
                        concept = cell.concept or cell.label or ""
                        explanation = cell.explanation or cell.definition or ""
                        if concept:
                            await self._emit(
                                {
                                    "type": "cell",
                                    "project_id": project_id,
                                    "row": r,
                                    "col": c,
                                    "concept": concept,
                                    "explanation": explanation,
                                }
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
            # Remove the task entry and clean up subscriber queues.
            # Both happen under the lock so readers see a consistent state.
            # The delay allows clients to receive the final SSE event before the
            # queue is torn down.
            async with self._lock:
                self._tasks.pop(project_id, None)
            await asyncio.sleep(2)
            async with self._lock:
                self._queues.pop(project_id, None)

    # ── Re-validation (user-comment-driven) ──────────────────────────────

    async def revalidate_matrix(self, project_id: str, user_comment: str) -> None:
        """Start a background validation-only pass, incorporating optional user comment."""
        if self.is_generating(project_id):
            raise ValueError("Already generating")
        project = await self._db.get_project(project_id)
        if project is None:
            raise ValueError("Project not found")
        await self._db.update_project_status(project_id, "generating")
        async with self._lock:
            self._queues.setdefault(project_id, [])
            task = asyncio.create_task(self._run_revalidation(project_id, user_comment))
            self._tasks[project_id] = task

    async def _run_revalidation(self, project_id: str, user_comment: str) -> None:
        """Validation-only background task: validate → swap → retry, then mark complete."""
        settings = self._settings
        try:
            project = await self._db.get_project(project_id)
            if project is None:
                raise ValueError("Project not found")

            all_cells = await self._db.get_all_cells(project_id)
            theme = project.theme
            input_mode = project.input_mode

            n_rows = project.effective_n_rows
            n_cols = project.effective_n_cols
            cells_grid = _build_grid(all_cells, n_rows, n_cols)

            # Reconstruct axes from stored cell descriptors
            if input_mode == "description":
                # row_axes[r] = row_descriptor from any cell in that row
                row_axes: List[str] = [""] * n_rows
                col_axes: List[str] = [""] * n_cols
                for cell in all_cells:
                    if cell.row_descriptor and not row_axes[cell.row]:
                        row_axes[cell.row] = cell.row_descriptor
                    if cell.col_descriptor and not col_axes[cell.col]:
                        col_axes[cell.col] = cell.col_descriptor
                axes_kw: Dict[str, Any] = {"row_axes": row_axes, "col_axes": col_axes}
            else:
                diag = {c.row: c for c in all_cells if c.row == c.col}
                axes_list: List[Tuple[str, str]] = [
                    (diag[i].row_descriptor or "", diag[i].col_descriptor or "")
                    if i in diag else ("", "")
                    for i in range(n_rows)
                ]
                axes_kw = {"axes": axes_list}

            failures: List[Tuple[int, int, str]] = []
            swaps: List[Tuple[int, int, int, int]] = []

            for attempt in range(settings.max_retries + 1):
                all_cells = await self._db.get_all_cells(project_id)
                cells_grid = _build_grid(all_cells, n_rows, n_cols)
                failures, swaps = await self._gen.validate_matrix(
                    project_id=project_id,
                    theme=theme,
                    cells_grid=cells_grid,
                    settings=settings,
                    emit=self._emit,
                    user_comment=user_comment,
                    **axes_kw,
                )
                if not failures and not swaps:
                    break
                if attempt < settings.max_retries:
                    logger.info(
                        "Revalidation %s: swapping %d pair(s), retrying %d cell(s) (attempt %d)",
                        project_id[:8], len(swaps), len(failures), attempt + 1,
                    )
                    await MatrixGenerator._backoff(attempt)
                    for ra, ca, rb, cb in swaps:
                        await self._apply_swap(project_id, ra, ca, rb, cb)
                    # Combine failure reason with user comment for regeneration
                    for r, c, reason in failures:
                        parts = [p for p in [reason, f"User feedback: {user_comment}" if user_comment else ""] if p]
                        extra = ". ".join(parts)
                        await self.regenerate_cell(
                            project_id=project_id,
                            row=r,
                            col=c,
                            extra_instructions=extra,
                        )

            # Restore any cells still shown as "generating" after exhausting retries
            if failures:
                for r, c, _ in failures:
                    cell = await self._db.get_cell(project_id, r, c)
                    if cell:
                        concept = cell.concept or cell.label or ""
                        explanation = cell.explanation or cell.definition or ""
                        if concept:
                            await self._emit({
                                "type": "cell",
                                "project_id": project_id,
                                "row": r,
                                "col": c,
                                "concept": concept,
                                "explanation": explanation,
                            })

            await self._db.update_project_status(project_id, "complete")
            await self._emit({"type": "done", "project_id": project_id})

        except asyncio.CancelledError:
            raise
        except GeminiError as exc:
            logger.error("Revalidation %s GeminiError: %s", project_id[:8], exc)
            await self._db.update_project_status(project_id, "failed", str(exc))
            await self._emit({"type": "error", "project_id": project_id, "message": str(exc)})
        except Exception as exc:
            logger.exception("Revalidation %s unexpected error", project_id[:8])
            await self._db.update_project_status(project_id, "failed", str(exc))
            await self._emit({"type": "error", "project_id": project_id, "message": str(exc)})
        finally:
            async with self._lock:
                self._tasks.pop(project_id, None)
            await asyncio.sleep(2)
            async with self._lock:
                self._queues.pop(project_id, None)

    # ── Swap helper ───────────────────────────────────────────────────────

    async def _apply_swap(
        self,
        project_id: str,
        row_a: int,
        col_a: int,
        row_b: int,
        col_b: int,
    ) -> None:
        """Swap the concept/explanation of two cells without any LLM call.

        Used when the validator determines that repositioning is cheaper than
        regeneration (e.g. two concepts that are each better suited to the
        other's position).
        """
        cell_a, cell_b = await self._db.swap_cells(
            project_id, row_a, col_a, row_b, col_b
        )
        if cell_a is None or cell_b is None:
            logger.warning(
                "Swap skipped: missing cell (%d,%d) or (%d,%d)",
                row_a, col_a, row_b, col_b,
            )
            return
        await self._emit({
            "type": "cell",
            "project_id": project_id,
            "row": row_a,
            "col": col_a,
            "concept": cell_a.concept or "",
            "explanation": cell_a.explanation or "",
        })
        await self._emit({
            "type": "cell",
            "project_id": project_id,
            "row": row_b,
            "col": col_b,
            "concept": cell_b.concept or "",
            "explanation": cell_b.explanation or "",
        })

    # ── Event broadcasting ────────────────────────────────────────────────

    async def _emit(self, event: Dict[str, Any]) -> None:
        """Push event to all subscriber queues for the project."""
        project_id = event.get("project_id", "")
        for q in list(self._queues.get(project_id, [])):
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
