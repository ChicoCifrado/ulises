"""Async utilities — safe task creation, background task helpers.

Use safe_create_task() instead of asyncio.create_task() for any
fire-and-forget coroutine so that unhandled exceptions are logged
instead of silently lost.
"""

import asyncio
import logging

_log = logging.getLogger(__name__)


def safe_create_task(coro, *, name: str | None = None, logger: logging.Logger | None = None) -> asyncio.Task:
    """Create an asyncio task and log any unhandled exception.

    Use this instead of ``asyncio.create_task()`` for fire-and-forget
    coroutines.  The returned task can still be awaited if the caller
    later changes its mind — the done-callback is idempotent.
    """
    task = asyncio.create_task(coro, name=name)
    task.add_done_callback(lambda t: _log_task_exception(t, logger))
    return task


def _log_task_exception(task: asyncio.Task, logger: logging.Logger | None = None) -> None:
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        (logger or _log).error(
            "Unhandled exception in fire-and-forget task '%s'",
            task.get_name(),
            exc_info=exc,
        )
