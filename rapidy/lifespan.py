import asyncio
import inspect
from contextlib import AbstractAsyncContextManager, asynccontextmanager, AsyncExitStack
from functools import partial
from typing import Any, AsyncGenerator, Awaitable, Callable, List, Optional, TYPE_CHECKING, Union

from typing_extensions import TypeAlias

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
SyncOrAsync: TypeAlias = Union[Any, Awaitable[Any]]

LifespanCTX = Union[CallableAsyncCTX, 'ABCAContextManager']  # type: ignore[type-arg]  # py3.8
LifespanHook: TypeAlias = Union[
    Callable[['Application'], SyncOrAsync],
    Callable[[], SyncOrAsync],
]


def is_async_callable(func: Callable[..., Any]) -> Any:
    base_function = func.func if isinstance(func, partial) else func

    return inspect.iscoroutinefunction(func) or (
        callable(base_function)
        and inspect.iscoroutinefunction(base_function.__call__)  # type: ignore[operator]  # noqa: WPS609
    )


class Lifespan:
    def __init__(
            self,
            app: 'Application',
            on_startup: List[LifespanHook],
            on_shutdown: List[LifespanHook],
            on_cleanup: List[LifespanHook],
            lifespan_managers: List[LifespanCTX],
    ) -> None:
        self._app = app
        self._lifespan_status_queue: Optional[asyncio.Queue[Any]] = None

        self.lifespan_managers = lifespan_managers
        self.on_startup = on_startup
        self.on_shutdown = on_shutdown
        self.on_cleanup = on_cleanup

    def append(self, lifespan: LifespanCTX) -> None:
        self.lifespan_managers.append(lifespan)

    @asynccontextmanager
    async def ctx_manager(self) -> AsyncGenerator[None, None]:
        # NOTE: This code is taken almost unchanged from the https://litestar.dev/ project.

        async with AsyncExitStack() as exit_stack:
            for cleanup_hook in self.on_cleanup[::-1]:
                exit_stack.push_async_callback(partial(self._call_lifespan_hook, cleanup_hook))

            for shutdown_hook in self.on_shutdown[::-1]:
                exit_stack.push_async_callback(partial(self._call_lifespan_hook, shutdown_hook))

            for manager in self.lifespan_managers:
                if not isinstance(manager, AbstractAsyncContextManager):
                    manager = manager(self._app)

                await exit_stack.enter_async_context(manager)

            for startup_hook in self.on_startup:
                await self._call_lifespan_hook(startup_hook)

            yield

    async def _call_lifespan_hook(self, hook: LifespanHook) -> None:
        ret = hook(self._app) if inspect.signature(hook).parameters else hook()  # type: ignore[call-arg]
        if is_async_callable(hook):
            await ret
