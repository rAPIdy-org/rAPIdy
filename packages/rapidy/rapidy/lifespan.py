from __future__ import annotations

import inspect
from contextlib import AbstractAsyncContextManager, asynccontextmanager, AsyncExitStack
from typing import Any, cast, TYPE_CHECKING

from rapidy.exceptions import ASGIProtocolError
from rapidy.typedefs import LifespanCTX, LifespanHook, Receive, Send

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from rapidy.application import Rapidy

__all__ = ('Lifespan', 'LifespanCTX', 'LifespanHook')


class Lifespan:
    """Application lifespan managers and hooks."""

    __slots__ = ('_app', 'lifespan_managers', 'on_cleanup', 'on_shutdown', 'on_startup')

    def __init__(
        self,
        app: Rapidy,
        *,
        on_startup: list[LifespanHook] | None = None,
        on_shutdown: list[LifespanHook] | None = None,
        on_cleanup: list[LifespanHook] | None = None,
        lifespan_managers: list[LifespanCTX] | None = None,
    ) -> None:
        self._app = app
        self.lifespan_managers = list(lifespan_managers or ())
        self.on_startup = list(on_startup or ())
        self.on_shutdown = list(on_shutdown or ())
        self.on_cleanup = list(on_cleanup or ())

    def append(self, lifespan: LifespanCTX) -> None:
        """Append a lifespan context manager or factory."""
        self.lifespan_managers.append(lifespan)

    async def _call_lifespan_hook(self, hook: LifespanHook) -> None:
        generic_hook = cast('Any', hook)
        result = generic_hook(self._app) if inspect.signature(hook).parameters else generic_hook()
        if inspect.isawaitable(result):
            await result

    async def _call_hooks(self, hooks: list[LifespanHook]) -> None:
        for hook in hooks:
            await self._call_lifespan_hook(hook)

    @asynccontextmanager
    async def ctx_manager(self) -> AsyncIterator[None]:
        """Enter managers and run hooks in the frozen lifecycle order."""
        async with AsyncExitStack() as stack:
            for source in self.lifespan_managers:
                manager = source(self._app) if callable(source) else source
                await stack.enter_async_context(cast('AbstractAsyncContextManager[Any]', manager))

            stack.push_async_callback(self._call_hooks, self.on_cleanup)
            stack.push_async_callback(self._call_hooks, self.on_shutdown)
            await self._call_hooks(self.on_startup)
            yield

    async def handle_asgi(self, receive: Receive, send: Send) -> None:
        """Drive one ASGI lifespan connection."""
        startup = await receive()
        if startup.get('type') != 'lifespan.startup':
            msg = f"Expected 'lifespan.startup', got {startup.get('type')!r}"
            raise ASGIProtocolError(msg)

        manager = self.ctx_manager()
        try:
            await manager.__aenter__()
        except BaseException as exc:
            await send({'type': 'lifespan.startup.failed', 'message': str(exc)})
            raise

        await send({'type': 'lifespan.startup.complete'})
        shutdown = await receive()
        if shutdown.get('type') != 'lifespan.shutdown':
            await manager.__aexit__(None, None, None)
            msg = f"Expected 'lifespan.shutdown', got {shutdown.get('type')!r}"
            raise ASGIProtocolError(msg)

        try:
            await manager.__aexit__(None, None, None)
        except BaseException as exc:
            await send({'type': 'lifespan.shutdown.failed', 'message': str(exc)})
            raise
        await send({'type': 'lifespan.shutdown.complete'})
