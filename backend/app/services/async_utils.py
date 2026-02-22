"""Shared async utilities for service layer concurrency patterns."""

from __future__ import annotations

import asyncio
from typing import Any, Coroutine, List, TypeVar

T = TypeVar("T")


async def bounded_gather(
    coros: List[Coroutine[Any, Any, T]],
    limit: int,
) -> List[T]:
    """Run coroutines concurrently with a maximum *limit* at a time.

    Equivalent to ``asyncio.gather(*coros)`` but caps the number of
    coroutines executing simultaneously via an ``asyncio.Semaphore``.
    """
    sem = asyncio.Semaphore(limit)

    async def _run(coro: Coroutine[Any, Any, T]) -> T:
        async with sem:
            return await coro

    return list(await asyncio.gather(*(_run(c) for c in coros)))
