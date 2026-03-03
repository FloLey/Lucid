"""Shared async utilities for service layer concurrency patterns."""

from __future__ import annotations

import asyncio
from typing import Any, Coroutine, List, TypeVar, Union

T = TypeVar("T")


async def bounded_gather(
    coros: List[Coroutine[Any, Any, T]],
    limit: int,
    return_exceptions: bool = False,
) -> List[Union[T, BaseException]]:
    """Run coroutines concurrently with a maximum *limit* at a time.

    Equivalent to ``asyncio.gather(*coros)`` but caps the number of
    coroutines executing simultaneously via an ``asyncio.Semaphore``.

    Args:
        coros: Coroutines to run.
        limit: Maximum number to run concurrently.
        return_exceptions: If True, exceptions are returned as results rather
            than propagated. Allows partial success — callers should check each
            result with ``isinstance(result, BaseException)``.
    """
    sem = asyncio.Semaphore(limit)

    async def _run(coro: Coroutine[Any, Any, T]) -> T:
        async with sem:
            return await coro

    return list(
        await asyncio.gather(
            *(_run(c) for c in coros), return_exceptions=return_exceptions
        )
    )
