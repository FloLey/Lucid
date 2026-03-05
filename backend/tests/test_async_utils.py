"""Tests for bounded_gather() async utility."""

import asyncio
import time

import pytest

from app.services.async_utils import bounded_gather
from tests.conftest import run_async


class TestBoundedGather:
    """Tests for bounded_gather()."""

    def test_invalid_limit_zero_raises(self):
        """limit=0 should raise ValueError before creating a broken Semaphore."""
        with pytest.raises(ValueError, match="limit must be >= 1"):
            run_async(bounded_gather([], limit=0))

    def test_invalid_limit_negative_raises(self):
        """Negative limit should raise ValueError."""
        with pytest.raises(ValueError, match="limit must be >= 1"):
            run_async(bounded_gather([], limit=-5))

    def test_empty_coros_returns_empty_list(self):
        """No coroutines → empty result."""
        result = run_async(bounded_gather([], limit=5))
        assert result == []

    def test_results_match_coro_outputs(self):
        """Results are returned in the same order as the input coroutines."""
        async def _val(n: int) -> int:
            return n * 2

        result = run_async(bounded_gather([_val(i) for i in range(5)], limit=3))
        assert result == [0, 2, 4, 6, 8]

    def test_exception_propagates_by_default(self):
        """Without return_exceptions=True, the first exception is raised."""
        async def _fail():
            raise RuntimeError("boom")

        async def _ok():
            return 42

        with pytest.raises(RuntimeError, match="boom"):
            run_async(bounded_gather([_fail(), _ok()], limit=2))

    def test_return_exceptions_captures_errors(self):
        """With return_exceptions=True, exceptions are returned as values."""
        async def _fail():
            raise ValueError("err")

        async def _ok():
            return 99

        results = run_async(
            bounded_gather([_ok(), _fail()], limit=2, return_exceptions=True)
        )
        assert results[0] == 99
        assert isinstance(results[1], ValueError)

    def test_concurrency_limit_is_respected(self):
        """At most `limit` coroutines run simultaneously."""
        running = 0
        peak = 0

        async def _track(delay: float) -> int:
            nonlocal running, peak
            running += 1
            peak = max(peak, running)
            await asyncio.sleep(delay)
            running -= 1
            return 1

        # 6 tasks each sleeping 0.05s, limit=2 → peak concurrency must be ≤ 2
        run_async(bounded_gather([_track(0.05) for _ in range(6)], limit=2))
        assert peak <= 2

    def test_limit_1_serialises_execution(self):
        """limit=1 forces sequential execution."""
        order: list[int] = []

        async def _append(n: int) -> int:
            order.append(n)
            await asyncio.sleep(0)  # yield, but still sequential with limit=1
            return n

        run_async(bounded_gather([_append(i) for i in range(4)], limit=1))
        assert order == [0, 1, 2, 3]
