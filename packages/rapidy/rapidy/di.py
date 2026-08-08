from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from rapidy.depends import (
    AsyncContainer,
    BaseScope,
    make_async_container,
    Provider,
    RapidyProvider,
    Scope,
    ValidationSettings,
)
from rapidy.request import Request

if TYPE_CHECKING:
    from rapidy.application import Rapidy

__all__ = ()

type LockFactory = Callable[[], AbstractAsyncContextManager[Any]]

DEFAULT_DI_LOCK_FACTORY: LockFactory = asyncio.Lock
DEFAULT_DI_VALIDATION_SETTINGS = ValidationSettings()


@dataclass(frozen=True, slots=True)
class DIConfig:
    """Frozen root-container construction policy owned by one application."""

    container: AsyncContainer | None
    providers: Sequence[Provider]
    scopes: type[BaseScope]
    context: dict[Any, Any] | None
    lock_factory: LockFactory | None
    skip_validation: bool
    start_scope: BaseScope | None
    validation_settings: ValidationSettings


def create_async_container(config: DIConfig) -> AsyncContainer:
    """Create the framework-owned root container through the core facade."""
    return make_async_container(
        *config.providers,
        RapidyProvider(),
        scopes=config.scopes,
        context=config.context,
        lock_factory=config.lock_factory,
        skip_validation=config.skip_validation,
        start_scope=config.start_scope,
        validation_settings=config.validation_settings,
    )


@asynccontextmanager
async def di_lifespan(app: Rapidy) -> AsyncIterator[None]:
    """Bind the root container for one ASGI lifespan and close only owned containers."""
    if app._root_app is not None:  # noqa: SLF001
        yield
        return

    config = app._di_config  # noqa: SLF001
    if config.container is None:
        container = create_async_container(config)
        app._di_container_owned = True  # noqa: SLF001
    else:
        container = config.container
        app._di_container_owned = False  # noqa: SLF001
    app._di_container_closed = False  # noqa: SLF001
    app.state.di_container = container
    try:
        yield
    finally:
        await close_owned_di(app)


async def close_owned_di(app: Rapidy) -> None:
    """Close the framework-owned root container at most once."""
    if not app._di_container_owned or app._di_container_closed:  # noqa: SLF001
        return
    container = app.state.get('di_container')
    if container is None:
        return
    app._di_container_closed = True  # noqa: SLF001
    await container.close()


@asynccontextmanager
async def request_di_scope(root_container: AsyncContainer, request: Request) -> AsyncIterator[AsyncContainer]:
    """Enter the HTTP request scope and expose it through request state."""
    async with root_container(context={Request: request}, scope=Scope.REQUEST) as request_container:
        request.state.di_container = request_container
        yield request_container
