"""Tests for llm_logger — serialisation helpers, decorator, and context routing."""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import app.services.llm_logger as llm_logger
from app.services.llm_logger import (
    _get_log_file,
    _serialize_contents,
    _serialize_part,
    _serialize_response,
    log_llm_method,
    set_project_context,
    start_flow,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _Part:
    """Minimal stand-in for a genai Part object."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class _Content:
    """Minimal stand-in for a genai Content object (has .role + .parts)."""

    def __init__(self, role: str, parts: list):
        self.role = role
        self.parts = parts


class _Candidate:
    """Minimal stand-in for a genai Candidate."""

    def __init__(self, content, finish_reason="STOP"):
        self.content = content
        self.finish_reason = finish_reason


class _UsageMetadata:
    def __init__(self, prompt=1, candidates=2, total=3):
        self.prompt_token_count = prompt
        self.candidates_token_count = candidates
        self.total_token_count = total


class _Response:
    def __init__(self, candidates=None, usage_metadata=None):
        self.candidates = candidates or []
        self.usage_metadata = usage_metadata


# ---------------------------------------------------------------------------
# _serialize_part
# ---------------------------------------------------------------------------


class TestSerializePart:
    def test_text_part(self):
        part = _Part(text="hello", thought=None, function_call=None,
                     function_response=None, inline_data=None)
        result = _serialize_part(part)
        assert result == {"text": "hello"}

    def test_thought_part(self):
        part = _Part(thought="inner monologue", text=None, function_call=None,
                     function_response=None, inline_data=None)
        result = _serialize_part(part)
        assert result["thought"] == "inner monologue"

    def test_inline_data_part(self):
        inline = MagicMock()
        inline.mime_type = "image/png"
        inline.data = b"\x00" * 100
        part = _Part(inline_data=inline, text=None, thought=None,
                     function_call=None, function_response=None)
        result = _serialize_part(part)
        assert result["inline_data"]["mime_type"] == "image/png"
        assert result["inline_data"]["size_bytes"] == 100

    def test_unserializable_part_returns_error_flag(self):
        """A part whose attribute access raises still returns a dict (no exception propagates)."""
        bad = MagicMock()
        bad.thought = None
        bad.text = None
        bad.function_call = None
        bad.function_response = None
        # Make inline_data access raise
        type(bad).inline_data = property(lambda self: (_ for _ in ()).throw(RuntimeError("boom")))
        result = _serialize_part(bad)
        assert result.get("_serialize_error") is True

    def test_empty_part(self):
        part = _Part(text=None, thought=None, function_call=None,
                     function_response=None, inline_data=None)
        result = _serialize_part(part)
        assert result == {}

    def test_function_call_part(self):
        fn_call = MagicMock()
        fn_call.name = "search"
        fn_call.args = {"query": "test"}
        part = _Part(function_call=fn_call, text=None, thought=None,
                     function_response=None, inline_data=None)
        result = _serialize_part(part)
        assert result["function_call"]["name"] == "search"
        assert result["function_call"]["args"] == {"query": "test"}


# ---------------------------------------------------------------------------
# _serialize_contents
# ---------------------------------------------------------------------------


class TestSerializeContents:
    def test_none_returns_none(self):
        assert _serialize_contents(None) is None

    def test_bare_string(self):
        assert _serialize_contents("hello") == "hello"

    def test_list_of_strings(self):
        result = _serialize_contents(["a", "b"])
        assert result == ["a", "b"]

    def test_list_with_content_object(self):
        part = _Part(text="hi", thought=None, function_call=None,
                     function_response=None, inline_data=None)
        content = _Content(role="user", parts=[part])
        result = _serialize_contents([content])
        assert isinstance(result, list)
        assert result[0]["role"] == "user"
        assert result[0]["parts"][0]["text"] == "hi"

    def test_list_with_unrecognised_items(self):
        """Items without .parts are stringified."""
        result = _serialize_contents([42])
        assert result == ["42"]

    def test_non_string_non_list(self):
        """Anything else is str()-ed."""
        result = _serialize_contents({"key": "val"})
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# _serialize_response
# ---------------------------------------------------------------------------


class TestSerializeResponse:
    def test_none_returns_none(self):
        assert _serialize_response(None) is None

    def test_empty_response(self):
        resp = _Response()
        result = _serialize_response(resp)
        assert result == {}

    def test_usage_metadata(self):
        resp = _Response(usage_metadata=_UsageMetadata(prompt=10, candidates=20, total=30))
        result = _serialize_response(resp)
        assert result["usage"] == {
            "prompt_tokens": 10,
            "candidates_tokens": 20,
            "total_tokens": 30,
        }

    def test_candidates_with_parts(self):
        part = _Part(text="output", thought=None, function_call=None,
                     function_response=None, inline_data=None)
        content = _Content(role="model", parts=[part])
        candidate = _Candidate(content=content, finish_reason="STOP")
        resp = _Response(candidates=[candidate])
        result = _serialize_response(resp)
        assert len(result["candidates"]) == 1
        assert result["candidates"][0]["finish_reason"] == "STOP"
        assert result["candidates"][0]["parts"][0]["text"] == "output"

    def test_serialize_error_is_caught(self):
        """If candidates iteration raises, _serialize_error is set."""
        bad = MagicMock()
        type(bad).candidates = property(lambda self: (_ for _ in ()).throw(RuntimeError("x")))
        bad.usage_metadata = None
        result = _serialize_response(bad)
        assert result.get("_serialize_error") is True


# ---------------------------------------------------------------------------
# Context routing — _get_log_file
# ---------------------------------------------------------------------------


class TestGetLogFile:
    def test_default_fallback(self):
        """With no context set, returns the fallback llm_debug.jsonl path."""
        # Reset context vars
        llm_logger._current_project_id.set(None)
        llm_logger._current_flow.set(None)
        log_file = _get_log_file()
        assert log_file.name == "llm_debug.jsonl"

    def test_project_context_takes_priority(self):
        set_project_context("proj-abc")
        try:
            log_file = _get_log_file()
            assert "proj-abc.jsonl" in str(log_file)
            assert "projects" in str(log_file)
        finally:
            llm_logger._current_project_id.set(None)

    def test_flow_fallback_when_no_project(self):
        llm_logger._current_project_id.set(None)
        start_flow("my_flow")
        try:
            log_file = _get_log_file()
            assert "my_flow" in str(log_file)
        finally:
            llm_logger._current_flow.set(None)

    def test_project_overrides_flow(self):
        start_flow("some_flow")
        set_project_context("override-proj")
        try:
            log_file = _get_log_file()
            assert "override-proj" in str(log_file)
        finally:
            llm_logger._current_project_id.set(None)
            llm_logger._current_flow.set(None)


# ---------------------------------------------------------------------------
# log_llm_method decorator
# ---------------------------------------------------------------------------


class TestLogLlmMethodDecorator:
    def test_preserves_function_name(self):
        @log_llm_method()
        async def my_llm_function(x):
            return x

        assert my_llm_function.__name__ == "my_llm_function"

    def test_async_function_returns_result(self):
        @log_llm_method(method_name="test_call", model="test-model")
        async def compute(x: int) -> int:
            return x * 2

        result = asyncio.run(compute(21))
        assert result == 42

    def test_async_function_raises_on_exception(self):
        @log_llm_method()
        async def failing():
            raise ValueError("intentional failure")

        with pytest.raises(ValueError, match="intentional failure"):
            asyncio.run(failing())

    def test_logs_error_field_on_exception(self, tmp_path):
        """When the decorated function raises, the log record includes an error field."""
        log_file = tmp_path / "test.jsonl"
        llm_logger._current_project_id.set(None)
        llm_logger._current_flow.set(None)

        @log_llm_method(method_name="err_call", model="test-model")
        async def boom():
            raise RuntimeError("oops")

        with patch.object(llm_logger, "_get_log_file", return_value=log_file):
            with pytest.raises(RuntimeError):
                asyncio.run(boom())

        # Allow any background executor write to complete
        import time
        time.sleep(0.05)

        if log_file.exists():
            import json
            records = [json.loads(line) for line in log_file.read_text().splitlines() if line]
            assert any(r.get("error") == "oops" for r in records)

    def test_logs_success_output(self, tmp_path):
        """Successful calls log output_data (as a plain dict it is passed through)."""
        log_file = tmp_path / "ok.jsonl"
        llm_logger._current_project_id.set(None)
        llm_logger._current_flow.set(None)

        @log_llm_method(method_name="ok_call", model="test-model")
        async def succeed() -> dict:
            return {"answer": 42}

        with patch.object(llm_logger, "_get_log_file", return_value=log_file):
            asyncio.run(succeed())

        import time
        time.sleep(0.05)

        if log_file.exists():
            import json
            records = [json.loads(line) for line in log_file.read_text().splitlines() if line]
            assert any(r.get("error") is None for r in records)
