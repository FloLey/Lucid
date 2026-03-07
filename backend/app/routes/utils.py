"""Shared route handler utilities to reduce boilerplate."""

import logging
from typing import Awaitable, Callable, Optional, TypeVar

from fastapi import HTTPException

from app.models.project import ProjectResponse, ProjectState
from app.services.gemini_service import GeminiError

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def execute_service_action(
    action: Callable[[], Awaitable[Optional[ProjectState]]],
    error_message: str,
) -> ProjectResponse:
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
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"{error_message}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=error_message)
    if not project:
        raise HTTPException(status_code=404, detail=error_message)
    return ProjectResponse(project=project)


def execute_config_action(action: Callable[[], T], error_message: str = "Config error") -> T:
    """Execute a synchronous config service action with standard error handling.

    Maps ValueError → 400, all other exceptions → 500.
    """
    try:
        return action()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"{error_message}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
