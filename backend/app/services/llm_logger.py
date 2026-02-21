"""JSONL debug logger for all LLM calls.

Always-on: logs are always written (no env-var toggle needed).
Creates one log file per project in backend/logs/projects/{project_id}.jsonl.
Falls back to backend/logs/llm_debug.jsonl when no project context is set.
"""

import asyncio
import contextvars
import functools
import inspect
import json
import logging
import os
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Callable

logger = logging.getLogger(__name__)

_ENABLED = True  # Always on — one file per project
_LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
_lock = threading.Lock()

# Context var holding the log file name for the current request/flow (fallback)
_current_flow: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "llm_flow", default=None
)

# Context var holding the current project_id for per-project log files
_current_project_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "llm_project_id", default=None
)

# Regex to strip UUIDs / hex session IDs from paths
_ID_PATTERN = re.compile(r"[0-9a-f]{8,}")


def set_project_context(project_id: str) -> None:
    """Set the current project for log routing.

    Call this at the start of any service method that processes a specific project.
    All LLM calls made within the same async context will be written to
    ``logs/projects/{project_id}.jsonl``.
    """
    _current_project_id.set(project_id)


def start_flow(name: str) -> str:
    """Start a new logging flow for the current async context.

    Call this at the beginning of a request. All subsequent log_llm_call()
    invocations within the same context will write to a dedicated file.
    Returns the flow identifier (used as the filename stem).
    """
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")[:-3]  # ms precision
    flow_id = f"{ts}_{name}"
    _current_flow.set(flow_id)
    return flow_id


def _flow_name_from_path(path: str) -> str:
    """Derive a short flow name from a request path like /api/chat/{id}/stream."""
    name = path.strip("/").removeprefix("api/")
    # Remove segments that look like IDs
    parts = [p for p in name.split("/") if not _ID_PATTERN.fullmatch(p)]
    return "_".join(parts) or "unknown"


def _get_log_file() -> Path:
    """Determine the log file path.

    Priority: per-project file > per-request flow file > fallback.
    """
    project_id = _current_project_id.get(None)
    if project_id:
        return _LOG_DIR / "projects" / f"{project_id}.jsonl"
    flow = _current_flow.get(None)
    if flow:
        return _LOG_DIR / f"{flow}.jsonl"
    return _LOG_DIR / "llm_debug.jsonl"


def _serialize_part(part: Any) -> dict:
    """Serialize a single genai Part to a JSON-safe dict."""
    result = {}
    try:
        if hasattr(part, "thought") and part.thought:
            result["thought"] = part.thought
        if hasattr(part, "text") and part.text:
            result["text"] = part.text
        if hasattr(part, "function_call") and part.function_call:
            fc = part.function_call
            result["function_call"] = {
                "name": getattr(fc, "name", None),
                "args": dict(fc.args) if hasattr(fc, "args") and fc.args else {},
            }
        if hasattr(part, "function_response") and part.function_response:
            fr = part.function_response
            result["function_response"] = {
                "name": getattr(fr, "name", None),
            }
        if hasattr(part, "inline_data") and part.inline_data:
            data = part.inline_data
            result["inline_data"] = {
                "mime_type": getattr(data, "mime_type", None),
                "size_bytes": len(data.data)
                if hasattr(data, "data") and data.data
                else 0,
            }
    except Exception:
        result["_serialize_error"] = True
    return result


def _serialize_contents(contents: Any) -> Any:
    """Walk Content/Part lists and serialize to JSON-safe structures."""
    if contents is None:
        return None
    if isinstance(contents, str):
        return contents
    if isinstance(contents, list):
        serialized: list[Any] = []
        for item in contents:
            if isinstance(item, str):
                serialized.append(item)
            elif hasattr(item, "parts"):
                serialized.append(
                    {
                        "role": getattr(item, "role", None),
                        "parts": [_serialize_part(p) for p in (item.parts or [])],
                    }
                )
            else:
                try:
                    serialized.append(str(item))
                except Exception:
                    serialized.append("<unserializable>")
        return serialized
    try:
        return str(contents)
    except Exception:
        return "<unserializable>"


def _serialize_response(response: Any) -> Optional[dict]:
    """Extract candidates, parts, and usage from a genai response."""
    if response is None:
        return None
    result: dict[str, Any] = {}
    try:
        if hasattr(response, "candidates") and response.candidates:
            candidates: list[dict[str, Any]] = []
            for c in response.candidates:
                candidate: dict[str, Any] = {
                    "finish_reason": str(getattr(c, "finish_reason", None)),
                }
                content = getattr(c, "content", None)
                if content and hasattr(content, "parts") and content.parts:
                    candidate["parts"] = [_serialize_part(p) for p in content.parts]
                candidates.append(candidate)
            result["candidates"] = candidates

        if hasattr(response, "usage_metadata") and response.usage_metadata:
            um = response.usage_metadata
            result["usage"] = {
                "prompt_tokens": getattr(um, "prompt_token_count", None),
                "candidates_tokens": getattr(um, "candidates_token_count", None),
                "total_tokens": getattr(um, "total_token_count", None),
            }
    except Exception:
        result["_serialize_error"] = True
    return result


def _write_log_sync(log_file: Path, line: str) -> None:
    """Write a single log line to disk under a threading lock (sync-safe)."""
    with _lock:
        try:
            _LOG_DIR.mkdir(parents=True, exist_ok=True)
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception as e:
            logger.warning("Failed to write LLM debug log: %s", e)


def log_llm_call(
    *,
    method: str,
    model: str,
    caller: Optional[str] = None,
    input_data: Any = None,
    output_data: Any = None,
    duration_ms: Optional[float] = None,
    error: Optional[str] = None,
    config_summary: Optional[dict] = None,
) -> None:
    """Write a single JSONL record. Returns immediately if logging is disabled."""
    if not _ENABLED:
        return

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "method": method,
        "model": model,
        "caller": caller,
        "duration_ms": round(duration_ms, 1) if duration_ms is not None else None,
        "input": _serialize_contents(input_data),
        "output": _serialize_response(output_data)
        if not isinstance(output_data, (str, dict))
        else output_data,
        "error": error,
        "config": config_summary,
    }

    try:
        line = json.dumps(record, default=str, ensure_ascii=False) + "\n"
    except Exception as e:
        logger.warning("Failed to serialize LLM debug record: %s", e)
        return

    log_file = _get_log_file()
    try:
        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, _write_log_sync, log_file, line)
    except RuntimeError:
        # No running event loop — write synchronously (e.g. during tests)
        _write_log_sync(log_file, line)


def log_llm_method(
    method_name: Optional[str] = None,
    model: Optional[str] = None,
    model_param: str = "model",
    input_params: Optional[list] = None,
    config_params: Optional[list] = None,
    caller: Optional[str] = None,
):
    """
    Decorator for LLM service methods that automatically logs calls.

    Args:
        method_name: Override method name in logs (defaults to function name)
        model: Fixed model name to use (overrides model_param extraction)
        model_param: Name of the parameter containing model name (if model not provided)
        input_params: List of parameter names to extract as input data
        config_params: List of parameter names to extract as config summary
        caller: Explicit caller identifier (e.g. "stage1_service.generate_slide_texts")
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Extract method name
            log_method_name = method_name or func.__name__

            # Extract model from parameters
            bound_args = inspect.signature(func).bind(*args, **kwargs)
            bound_args.apply_defaults()
            effective_model = (
                model
                if model is not None
                else bound_args.arguments.get(model_param, "unknown")
            )

            # Extract input data
            input_data = {}
            if input_params:
                for param in input_params:
                    if param in bound_args.arguments:
                        value = bound_args.arguments[param]
                        # Truncate long strings
                        if isinstance(value, str) and len(value) > 500:
                            input_data[param] = value[:500] + "..."
                        else:
                            input_data[param] = value

            # Extract config summary
            config_summary = {}
            if config_params:
                for param in config_params:
                    if param in bound_args.arguments:
                        config_summary[param] = bound_args.arguments[param]

            # Time the call
            start = timer()
            error = None
            output_data = None

            try:
                result = await func(*args, **kwargs)
                output_data = result
                return result
            except Exception as e:
                error = str(e)
                raise
            finally:
                duration = elapsed_ms(start)
                log_llm_call(
                    method=log_method_name,
                    model=effective_model,
                    caller=caller,
                    input_data=input_data if input_data else None,
                    output_data=output_data,
                    duration_ms=duration,
                    error=error,
                    config_summary=config_summary if config_summary else None,
                )

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Extract method name
            log_method_name = method_name or func.__name__

            # Extract model from parameters
            bound_args = inspect.signature(func).bind(*args, **kwargs)
            bound_args.apply_defaults()
            effective_model = (
                model
                if model is not None
                else bound_args.arguments.get(model_param, "unknown")
            )

            # Extract input data
            input_data = {}
            if input_params:
                for param in input_params:
                    if param in bound_args.arguments:
                        value = bound_args.arguments[param]
                        # Truncate long strings
                        if isinstance(value, str) and len(value) > 500:
                            input_data[param] = value[:500] + "..."
                        else:
                            input_data[param] = value

            # Extract config summary
            config_summary = {}
            if config_params:
                for param in config_params:
                    if param in bound_args.arguments:
                        config_summary[param] = bound_args.arguments[param]

            # Time the call
            start = timer()
            error = None
            output_data = None

            try:
                result = func(*args, **kwargs)
                output_data = result
                return result
            except Exception as e:
                error = str(e)
                raise
            finally:
                duration = elapsed_ms(start)
                log_llm_call(
                    method=log_method_name,
                    model=effective_model,
                    caller=caller,
                    input_data=input_data if input_data else None,
                    output_data=output_data,
                    duration_ms=duration,
                    error=error,
                    config_summary=config_summary if config_summary else None,
                )

        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def timer() -> float:
    """Return a high-resolution monotonic timestamp for timing LLM calls."""
    return time.monotonic()


def elapsed_ms(start: float) -> float:
    """Calculate elapsed time in milliseconds relative to the start timestamp."""
    return (time.monotonic() - start) * 1000
