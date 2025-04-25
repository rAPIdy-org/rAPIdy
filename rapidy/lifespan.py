from __future__ import annotations

import asyncio
import inspect
from contextlib import AbstractAsyncContextManager, asynccontextmanager, AsyncExitStack
from functools import partial
from typing import Any, AsyncGenerator, Awaitable, Callable, List, TYPE_CHECKING, Union
from typing_extensions import TypeAlias

from rapidy.annotation_checkers import is_async_callable
from rapidy.version import PY_VERSION_TUPLE

if TYPE_CHECKING:
    from web_app import Application

    if PY_VERSION_TUPLE < (1, 9, 0):
        ABCAContextManager = AbstractAsyncContextManager
    else:
        ABCAContextManager = AbstractAsyncContextManager[Any]  # type: ignore[assignment, misc, unused-ignore]

__all__ = (
    'LifespanCTX',
    'LifespanHook',
)

CallableAsyncCTX = Callable[['Application'], 'ABCAContextManager']  # type: ignore[type-arg]  # py3.8
SyncOrAsync: TypeAlias = Any | Awaitable[Any]

LifespanCTX = Union[CallableAsyncCTX, 'ABCAContextManager']  # type: ignore[type-arg]  # py3.8
LifespanHook: TypeAlias = Callable[['Application'], SyncOrAsync] | Callable[[], SyncOrAsync]


class Lifespan:
    """Lifespan manager for the application.

    This class manages the application's lifecycle by coordinating startup, shutdown, and cleanup
    hooks, as well as managing lifespan context managers.

    Attributes:
        _app (Application): The application instance.
        _lifespan_status_queue (Optional[asyncio.Queue[Any]]): Queue for managing lifespan status.
        lifespan_managers (List[LifespanCTX]): List of lifespan context managers.
        on_startup (List[LifespanHook]): List of startup hooks.
        on_shutdown (List[LifespanHook]): List of shutdown hooks.
        on_cleanup (List[LifespanHook]): List of cleanup hooks.

    Methods:
        append(lifespan: LifespanCTX) -> None: Appends a new lifespan context manager.
        ctx_manager() -> AsyncGenerator[None, None]: Asynchronous context manager to manage lifespan.
        _call_lifespan_hook(hook: LifespanHook) -> None: Calls a lifespan hook function.
    """

    def __init__(
        self,
        app: Application,
        on_startup: List[LifespanHook],
        on_shutdown: List[LifespanHook],
        on_cleanup: List[LifespanHook],
        lifespan_managers: List[LifespanCTX],
    ) -> None:
        """Initializes the Lifespan manager.

        Args:
            app (Application): The application instance.
            on_startup (List[LifespanHook]): List of startup hooks.
            on_shutdown (List[LifespanHook]): List of shutdown hooks.
            on_cleanup (List[LifespanHook]): List of cleanup hooks.
            lifespan_managers (List[LifespanCTX]): List of lifespan context managers.
        """
        self._app = app
        self._lifespan_status_queue: asyncio.Queue[Any] | None = None

        self.lifespan_managers = lifespan_managers
        self.on_startup = on_startup
        self.on_shutdown = on_shutdown
        self.on_cleanup = on_cleanup

    def append(self, lifespan: LifespanCTX) -> None:
        """Appends a new lifespan context manager.

        Args:
            lifespan (LifespanCTX): The lifespan context manager to append.
        """
        self.lifespan_managers.append(lifespan)

    @asynccontextmanager
    async def ctx_manager(self) -> AsyncGenerator[None, None]:
        """Asynchronous context manager for managing the lifespan.

        This context manager is responsible for managing the application's startup, shutdown,
        and cleanup hooks, as well as entering and exiting lifespan context managers.

        Yields:
            None: This function doesn't return any value.
        """
        # NOTE: This code is taken almost unchanged from the https://litestar.dev/ project.

        async with AsyncExitStack() as exit_stack:
            # Push cleanup hooks to exit stack
            for cleanup_hook in self.on_cleanup[::-1]:
                exit_stack.push_async_callback(partial(self._call_lifespan_hook, cleanup_hook))

            # Push shutdown hooks to exit stack
            for shutdown_hook in self.on_shutdown[::-1]:
                exit_stack.push_async_callback(partial(self._call_lifespan_hook, shutdown_hook))

            # Enter lifespan context managers
            for manager in self.lifespan_managers:
                if not isinstance(manager, AbstractAsyncContextManager):
                    manager = manager(self._app)  # noqa: PLW2901

                await exit_stack.enter_async_context(manager)

            # Execute startup hooks
            for startup_hook in self.on_startup:
                await self._call_lifespan_hook(startup_hook)

            yield

    async def _call_lifespan_hook(self, hook: LifespanHook) -> None:
        """Calls a lifespan hook.

        This method invokes the provided lifespan hook, checking if it requires the application
        or no arguments, and awaiting it if necessary.

        Args:
            hook (LifespanHook): The lifespan hook to call.

        Raises:
            Exception: If the hook raises an exception during execution.
        """
        ret = hook(self._app) if inspect.signature(hook).parameters else hook()  # type: ignore[call-arg]
        if is_async_callable(hook):
            await ret
