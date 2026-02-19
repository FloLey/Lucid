"""Shared route handler utilities to reduce boilerplate."""

import logging
from typing import Awaitable, Callable, Optional

from fastapi import HTTPException

from app.models.project import ProjectState
from app.services.gemini_service import GeminiError

logger = logging.getLogger(__name__)


async def execute_service_action(
    action: Callable[[], Awaitable[Optional[ProjectState]]],
    error_message: str,
) -> dict:
    """Execute an async service action with standard error handling.

    This utility wraps the repetitive pattern of:
    1. Executing an async service method.
    2. Catching specific GeminiErrors to propagate them.
    3. Catching generic exceptions for 500 logging.
    4. Validating the project exists before returning a model_dump.

    Returns:
        A dictionary containing the serialised project state.
    """
    try:
        project = await action()
    except GeminiError:
        raise
    except Exception as e:
        logger.error(f"{error_message}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"{error_message}: {e}")
    if not project:
        raise HTTPException(status_code=404, detail=error_message)
    return {"project": project.model_dump()}
