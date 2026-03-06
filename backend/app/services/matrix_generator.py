"""LLM pipeline for the Concept Matrix Generator.

Handles all Gemini calls; does NOT touch the database or SSE queues directly.
Instead it calls the provided `emit` callback after each result so the caller
(MatrixService) can persist and broadcast simultaneously.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple

from app.models.matrix import MatrixSettings
from app.services.async_utils import bounded_gather
from app.services.gemini_service import GeminiError, GeminiService
from app.services.image_service import ImageService
from app.services.prompt_loader import PromptLoader
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

# Type alias for the event-emitter callback
EventEmitter = Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]


class MatrixGenerator:
    """Stateless LLM pipeline. Each method takes an emit callback."""

    def __init__(
        self,
        gemini_service: GeminiService,
        image_service: ImageService,
        storage_service: StorageService,
        prompt_loader: PromptLoader,
    ) -> None:
        self._gemini_service = gemini_service
        self._image_service = image_service
        self._storage_service = storage_service
        self._prompt_loader = prompt_loader

    # ── Prompt helpers ────────────────────────────────────────────────────

    def _get_prompt(self, name: str) -> str:
        template = self._prompt_loader.get_cached(name)
        if not template:
            raise RuntimeError(f"Matrix prompt '{name}' not found")
        return template

    # ── Step 1: Diagonal concepts (1 LLM call) ───────────────────────────

    async def generate_diagonal(
        self,
        project_id: str,
        theme: str,
        n: int,
        language: str,
        style_mode: str,
        settings: MatrixSettings,
        emit: EventEmitter,
    ) -> List[Dict[str, str]]:
        """
        Generate n seed concepts for the diagonal.
        Returns [{label, definition}, ...].
        Emits one 'diagonal' event per concept.
        """
        prompt = self._get_prompt("matrix_diagonal").format(
            theme=theme,
            n=n,
            language=language,
            style_mode=style_mode,
        )
        raw = await self._gemini_service.generate_json(
            prompt=prompt,
            temperature=settings.diagonal_temperature,
            caller="matrix_diagonal",
        )
        concepts: List[Dict[str, str]] = raw.get("concepts", [])[:n]
        if len(concepts) < n:
            raise GeminiError(
                f"Diagonal generation returned {len(concepts)} concepts, expected {n}"
            )
        for i, concept in enumerate(concepts):
            await emit(
                {
                    "type": "diagonal",
                    "project_id": project_id,
                    "index": i,
                    "label": concept.get("label", ""),
                    "definition": concept.get("definition", ""),
                }
            )
        return concepts

    # ── Step 2: Axes per diagonal concept (n parallel calls) ─────────────

    async def generate_axes_for_concept(
        self,
        project_id: str,
        diagonal_index: int,
        concept: Dict[str, str],
        all_concepts: List[Dict[str, str]],
        settings: MatrixSettings,
        emit: EventEmitter,
    ) -> Tuple[str, str]:
        """
        Generate row/col descriptors for one diagonal concept.
        Returns (row_descriptor, col_descriptor).
        Emits one 'axes' event.
        """
        prompt = self._get_prompt("matrix_axes").format(
            index=diagonal_index,
            concept_label=concept.get("label", ""),
            concept_definition=concept.get("definition", ""),
            all_concepts_json=json.dumps(
                [c.get("label", "") for c in all_concepts]
            ),
        )
        raw = await self._gemini_service.generate_json(
            prompt=prompt,
            temperature=settings.axes_temperature,
            caller="matrix_axes",
        )
        row_desc = raw.get("row_descriptor", "")
        col_desc = raw.get("col_descriptor", "")
        await emit(
            {
                "type": "axes",
                "project_id": project_id,
                "row": diagonal_index,
                "col": diagonal_index,
                "row_descriptor": row_desc,
                "col_descriptor": col_desc,
            }
        )
        return row_desc, col_desc

    # ── Step 3: Off-diagonal cell (one LLM call) ─────────────────────────

    async def generate_cell(
        self,
        project_id: str,
        row: int,
        col: int,
        row_concept: Dict[str, str],
        col_concept: Dict[str, str],
        row_descriptor: str,
        col_descriptor: str,
        already_used_labels: List[str],
        theme: str,
        style_mode: str,
        settings: MatrixSettings,
        emit: EventEmitter,
        extra_instructions: str = "",
    ) -> Dict[str, str]:
        """
        Generate a concept for one off-diagonal cell.
        Returns {"concept": str, "explanation": str}.
        Emits one 'cell' event.
        """
        prompt = self._get_prompt("matrix_cell").format(
            theme=theme,
            style_mode=style_mode,
            row_label=row_concept.get("label", ""),
            col_label=col_concept.get("label", ""),
            row_descriptor=row_descriptor,
            col_descriptor=col_descriptor,
            already_used_labels=", ".join(already_used_labels) or "none",
            extra_instructions=extra_instructions,
        )
        raw = await self._gemini_service.generate_json(
            prompt=prompt,
            temperature=settings.cell_temperature,
            caller="matrix_cell",
        )
        concept = raw.get("concept", "")
        explanation = raw.get("explanation", "")
        await emit(
            {
                "type": "cell",
                "project_id": project_id,
                "row": row,
                "col": col,
                "concept": concept,
                "explanation": explanation,
            }
        )
        return {"concept": concept, "explanation": explanation}

    # ── Step 4: Validate the matrix (one LLM call) ───────────────────────

    async def validate_matrix(
        self,
        project_id: str,
        theme: str,
        cells_grid: List[List[Dict[str, str]]],
        settings: MatrixSettings,
        emit: EventEmitter,
        axes: Optional[List[Tuple[str, str]]] = None,
        row_axes: Optional[List[str]] = None,
        col_axes: Optional[List[str]] = None,
    ) -> List[Tuple[int, int]]:
        """
        Validate all cells (off-diagonal only in theme mode; all in description mode).
        Returns [(row, col), ...] of failing cells.
        Emits one 'validation' event.

        For theme mode: pass ``axes`` (List[Tuple[row_desc, col_desc]]).
        For description mode: pass ``row_axes`` and ``col_axes`` separately.
        """
        # Build matrix payload for the prompt
        matrix_data = []
        n_rows = len(cells_grid)
        n_cols = len(cells_grid[0]) if cells_grid else 0
        is_square_theme = n_rows == n_cols and axes is not None

        for r in range(n_rows):
            for c in range(n_cols):
                # In theme mode, skip diagonal cells (they are pre-seeded concepts)
                if is_square_theme and r == c:
                    continue
                if row_axes is not None and col_axes is not None:
                    row_desc = row_axes[r] if r < len(row_axes) else ""
                    col_desc = col_axes[c] if c < len(col_axes) else ""
                elif axes is not None:
                    row_desc = axes[r][0] if r < len(axes) else ""
                    col_desc = axes[c][1] if c < len(axes) else ""
                else:
                    row_desc = col_desc = ""
                matrix_data.append(
                    {
                        "row": r,
                        "col": c,
                        "row_descriptor": row_desc,
                        "col_descriptor": col_desc,
                        "concept": cells_grid[r][c].get("concept", ""),
                        "explanation": cells_grid[r][c].get("explanation", ""),
                    }
                )
        prompt = self._get_prompt("matrix_validator").format(
            theme=theme,
            matrix_json=json.dumps(matrix_data, ensure_ascii=False),
        )
        try:
            raw = await self._gemini_service.generate_json(
                prompt=prompt,
                temperature=settings.validation_temperature,
                caller="matrix_validator",
            )
            failures_raw = raw.get("failures", [])
        except GeminiError:
            logger.warning("Validation call failed; treating all cells as valid")
            failures_raw = []

        failures = [(f["row"], f["col"]) for f in failures_raw if "row" in f and "col" in f]
        await emit(
            {
                "type": "validation",
                "project_id": project_id,
                "failures": [{"row": r, "col": c} for r, c in failures],
            }
        )
        return failures

    # ── Step 5: Image per cell (optional) ────────────────────────────────

    async def generate_cell_image(
        self,
        project_id: str,
        row: int,
        col: int,
        concept: str,
        context: str,
        settings: MatrixSettings,
        emit: EventEmitter,
    ) -> str:
        """
        Generate and save an image for one cell.
        Returns the /images/<uuid>.png URL.
        Emits one 'image' event.
        """
        prompt_template = self._get_prompt("matrix_image_builder")
        image_prompt = prompt_template.format(
            concept=concept,
            context=context,
        )
        b64 = await self._image_service.generate_image(image_prompt)
        image_url = await asyncio.to_thread(
            self._storage_service.save_image_to_disk, b64
        )
        await emit(
            {
                "type": "image",
                "project_id": project_id,
                "row": row,
                "col": col,
                "image_url": image_url,
            }
        )
        return image_url

    # ── Description mode: axes + labels in one call ───────────────────────

    async def generate_from_description(
        self,
        project_id: str,
        description: str,
        n_rows: int,
        n_cols: int,
        language: str,
        style_mode: str,
        settings: MatrixSettings,
        emit: EventEmitter,
    ) -> Tuple[List[Dict[str, str]], List[Dict[str, str]], List[str], List[str]]:
        """
        Single LLM call: derive axes and separate row/col labels from a description.

        Returns (row_concepts, col_concepts, row_axes, col_axes) where:
        - row_concepts: [{label, definition}, ...] length n_rows
        - col_concepts: [{label, definition}, ...] length n_cols
        - row_axes: [row_descriptor_string, ...] length n_rows
        - col_axes: [col_descriptor_string, ...] length n_cols
        """
        # Sanitize user input to prevent breaking out of the XML delimiter in the prompt template.
        safe_description = description.replace("</user_description>", "&lt;/user_description&gt;")
        prompt = self._get_prompt("matrix_description_axes").format(
            description=safe_description,
            n_rows=n_rows,
            n_cols=n_cols,
            language=language,
            style_mode=style_mode,
        )
        raw = await self._gemini_service.generate_json(
            prompt=prompt,
            temperature=settings.diagonal_temperature,
            caller="matrix_description_axes",
        )
        row_axis_label = raw.get("row_axis_label", "Row")
        col_axis_label = raw.get("col_axis_label", "Col")

        row_labels: List[str] = raw.get("row_labels", [])[:n_rows]
        row_definitions: List[str] = raw.get("row_definitions", [])[:n_rows]
        col_labels: List[str] = raw.get("col_labels", [])[:n_cols]
        col_definitions: List[str] = raw.get("col_definitions", [])[:n_cols]

        if len(row_labels) < n_rows:
            raise GeminiError(
                f"Description axes returned {len(row_labels)} row labels, expected {n_rows}"
            )
        if len(col_labels) < n_cols:
            raise GeminiError(
                f"Description axes returned {len(col_labels)} col labels, expected {n_cols}"
            )

        # Pad definitions if the model returned fewer than expected
        while len(row_definitions) < n_rows:
            row_definitions.append("")
        while len(col_definitions) < n_cols:
            col_definitions.append("")

        row_concepts: List[Dict[str, str]] = [
            {"label": row_labels[i], "definition": row_definitions[i]} for i in range(n_rows)
        ]
        col_concepts: List[Dict[str, str]] = [
            {"label": col_labels[j], "definition": col_definitions[j]} for j in range(n_cols)
        ]
        row_axes = [f"{row_axis_label} {row_labels[i]}" for i in range(n_rows)]
        col_axes = [f"{col_axis_label} {col_labels[j]}" for j in range(n_cols)]

        # Emit axes events so the frontend can show header labels as they arrive
        for i, row_desc in enumerate(row_axes):
            await emit(
                {
                    "type": "axes",
                    "project_id": project_id,
                    "row": i,
                    "col": i,
                    "row_descriptor": row_desc,
                    "col_descriptor": col_axes[i] if i < len(col_axes) else "",
                }
            )

        return row_concepts, col_concepts, row_axes, col_axes

    # ── Retry helper ──────────────────────────────────────────────────────

    @staticmethod
    async def _backoff(attempt: int) -> None:
        """Exponential backoff with jitter: 2^attempt seconds ± 0-1 s."""
        delay = min(2**attempt, 16) + random.uniform(0, 1)
        await asyncio.sleep(delay)
