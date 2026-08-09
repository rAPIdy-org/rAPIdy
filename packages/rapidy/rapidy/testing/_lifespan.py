from __future__ import annotations

from collections.abc import Sequence
from contextlib import AbstractAsyncContextManager
from dataclasses import replace
from typing import Any, cast

from rapidy.application import Rapidy
from rapidy.depends import Provider
from rapidy.di import DIConfig

_ACTIVE_CLIENT_KEY = '_rapidy_testing_lifespan'


class TestLifespan:
    """Own one application's lifespan and temporary DI provider overrides."""

    __slots__ = ('_app', '_di_providers', '_manager', '_original_di_config', '_started')

    def __init__(self, app: Rapidy, di_providers: Sequence[Provider]) -> None:
        self._app = app
        self._di_providers = tuple(di_providers)
        self._manager: AbstractAsyncContextManager[Any] | None = None
        self._original_di_config: DIConfig | None = None
        self._started = False

    @property
    def started(self) -> bool:
        """Return whether this manager currently owns the application lifespan."""
        return self._started

    async def start(self) -> None:
        """Apply test providers and start the application exactly once."""
        if self._started:
            msg = 'Test client lifespan is already running'
            raise RuntimeError(msg)
        if self._app.state.get(_ACTIVE_CLIENT_KEY) is not None:
            msg = 'Another test client already owns this application lifespan'
            raise RuntimeError(msg)

        config = self._app._di_config  # noqa: SLF001
        if self._di_providers and config.container is not None:
            msg = 'DI provider overrides cannot be combined with an externally owned container'
            raise ValueError(msg)

        self._original_di_config = config
        if self._di_providers:
            self._app._di_config = replace(  # noqa: SLF001
                config,
                providers=(*config.providers, *self._di_providers),
            )
        self._app.state[_ACTIVE_CLIENT_KEY] = self
        manager = cast('AbstractAsyncContextManager[Any]', self._app.lifespan.ctx_manager())
        self._manager = manager
        try:
            await manager.__aenter__()
        except BaseException:
            self._restore()
            raise
        self._started = True

    async def close(self) -> None:
        """Stop the application and restore its production DI configuration."""
        manager, self._manager = self._manager, None
        if manager is None:
            self._restore()
            return
        try:
            await manager.__aexit__(None, None, None)
        finally:
            self._started = False
            self._restore()

    def _restore(self) -> None:
        if self._app.state.get(_ACTIVE_CLIENT_KEY) is self:
            del self._app.state[_ACTIVE_CLIENT_KEY]
        if self._original_di_config is not None:
            self._app._di_config = self._original_di_config  # noqa: SLF001
            self._original_di_config = None
