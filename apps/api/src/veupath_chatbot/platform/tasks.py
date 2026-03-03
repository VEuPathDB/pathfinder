"""Helpers for fire-and-forget asyncio background tasks.

``asyncio.create_task`` returns a ``Task`` that **must** be stored in a
strong reference; otherwise the garbage collector can cancel the task
mid-execution.  The ``spawn`` helper below retains every task in a
module-level set until it finishes.

See: https://docs.python.org/3/library/asyncio-task.html#creating-tasks
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any

_background_tasks: set[asyncio.Task[Any]] = set()


def spawn(
    coro: Coroutine[Any, Any, Any], *, name: str | None = None
) -> asyncio.Task[Any]:
    """Schedule *coro* as a background task with reference retention.

    The returned ``Task`` is kept alive until completion, after which it
    is automatically discarded.
    """
    task = asyncio.create_task(coro, name=name)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task
