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
        axes: List[Tuple[str, str]],
        settings: MatrixSettings,
        emit: EventEmitter,
    ) -> List[Tuple[int, int]]:
        """
        Validate all off-diagonal cells.
        Returns [(row, col), ...] of failing cells.
        Emits one 'validation' event.
        """
        # Build matrix payload for the prompt
        matrix_data = []
        n = len(cells_grid)
        for r in range(n):
            for c in range(n):
                if r == c:
                    continue
                matrix_data.append(
                    {
                        "row": r,
                        "col": c,
                        "row_descriptor": axes[r][0] if r < len(axes) else "",
                        "col_descriptor": axes[c][1] if c < len(axes) else "",
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
        n: int,
        language: str,
        style_mode: str,
        settings: MatrixSettings,
        emit: EventEmitter,
    ) -> Tuple[List[Dict[str, str]], List[Tuple[str, str]]]:
        """
        Single LLM call: derive axes and labels from a description.
        Returns (concepts, axes_results) in the same shape expected by _run_pipeline.
        Emits axes events only (no diagonal events — all cells are generated equally
        in description mode, diagonal cells are not pre-populated).
        """
        prompt = self._get_prompt("matrix_description_axes").format(
            description=description,
            n=n,
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
        labels: List[str] = raw.get("labels", [])[:n]
        definitions: List[str] = raw.get("definitions", [])[:n]

        if len(labels) < n:
            raise GeminiError(
                f"Description axes returned {len(labels)} labels, expected {n}"
            )

        # Pad definitions if the model returned fewer than expected
        while len(definitions) < n:
            definitions.append("")

        concepts: List[Dict[str, str]] = [
            {"label": labels[i], "definition": definitions[i]} for i in range(n)
        ]
        axes_results: List[Tuple[str, str]] = [
            (f"{row_axis_label} {labels[i]}", f"{col_axis_label} {labels[i]}")
            for i in range(n)
        ]

        # Emit axes events (reuse existing event structure)
        # Note: no diagonal events — in description mode all cells are generated
        # equally (including diagonal), so we don't pre-populate them here.
        for i, (row_desc, col_desc) in enumerate(axes_results):
            await emit(
                {
                    "type": "axes",
                    "project_id": project_id,
                    "row": i,
                    "col": i,
                    "row_descriptor": row_desc,
                    "col_descriptor": col_desc,
                }
            )

        return concepts, axes_results

    # ── Retry helper ──────────────────────────────────────────────────────

    @staticmethod
    async def _backoff(attempt: int) -> None:
        """Exponential backoff with jitter: 2^attempt seconds ± 0-1 s."""
        delay = min(2**attempt, 16) + random.uniform(0, 1)
        await asyncio.sleep(delay)
