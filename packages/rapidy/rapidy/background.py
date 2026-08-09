from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from contextvars import copy_context
from inspect import isawaitable, iscoroutinefunction

__all__ = ('BackgroundTask', 'BackgroundTasks')


class BackgroundTask:
    """Run one callable after the final response body frame.

    The construction context is retained so request IDs and other context variables
    remain available even though middleware unwinds before the response is sent.
    """

    __slots__ = ('_args', '_context', '_func', '_kwargs')

    def __init__[**P](
        self,
        func: Callable[P, Awaitable[None] | None],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self._context = copy_context()

    async def __call__(self) -> None:
        """Await the task to completion without detaching it from the request."""
        task = asyncio.create_task(self._run(), context=self._context.copy())
        await task

    async def _run(self) -> None:
        if iscoroutinefunction(self._func):
            await self._func(*self._args, **self._kwargs)
            return
        result = await asyncio.to_thread(self._func, *self._args, **self._kwargs)
        if isawaitable(result):
            await result


class BackgroundTasks:
    """Execute background tasks sequentially in registration order."""

    __slots__ = ('_tasks',)

    def __init__(self, tasks: Sequence[BackgroundTask] | None = None) -> None:
        prepared = list(tasks or ())
        if not all(isinstance(task, BackgroundTask) for task in prepared):
            msg = 'tasks must contain only BackgroundTask instances'
            raise TypeError(msg)
        self._tasks = prepared

    @property
    def tasks(self) -> tuple[BackgroundTask, ...]:
        """Return the immutable registered task view."""
        return tuple(self._tasks)

    def add_task[**P](
        self,
        func: Callable[P, Awaitable[None] | None],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        """Register one typed callable and capture the current context."""
        self._tasks.append(BackgroundTask(func, *args, **kwargs))

    async def __call__(self) -> None:
        """Run tasks in order, stopping on the first failure or cancellation."""
        for task in tuple(self._tasks):
            await task()


type Background = BackgroundTask | BackgroundTasks
type BackgroundCallable = Callable[[], Awaitable[None] | None]
type BackgroundRunner = Callable[[], Awaitable[None]]


def normalize_background(background: Background | BackgroundCallable | None) -> BackgroundRunner | None:
    """Validate and normalize the response-level background contract."""
    if background is None or isinstance(background, (BackgroundTask, BackgroundTasks)):
        return background
    if callable(background):
        return BackgroundTask(background)
    msg = 'background must be BackgroundTask, BackgroundTasks, a callable, or None'
    raise TypeError(msg)
