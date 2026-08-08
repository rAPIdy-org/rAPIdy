from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from functools import partial
from typing import Any, TYPE_CHECKING

import pytest

from rapidy import Rapidy

if TYPE_CHECKING:
    from rapidy.lifespan import CallableAsyncCTX
    from tests.ported.client import AppClientFactory


# note: not using `unittest.mock.AsyncMock` because in some versions of python there is an error:
# TypeError: 'Mock' object is not subscriptable.
class HookMock:
    def __init__(self) -> None:
        self.call_count = 0

    async def __call__(self, *args: Any, **kwargs: Any) -> None:
        self.call_count += 1


class SomeError(Exception):
    pass


@pytest.fixture
def startup_mock() -> HookMock:
    return HookMock()


@pytest.fixture
def shutdown_mock() -> HookMock:
    return HookMock()


@pytest.fixture
def cleanup_mock() -> HookMock:
    return HookMock()


@pytest.fixture
def callable_async_ctx(startup_mock: HookMock, shutdown_mock: HookMock) -> CallableAsyncCTX:
    @asynccontextmanager
    async def _async_ctx(app: Rapidy) -> AsyncGenerator[None, None]:
        try:
            await startup_mock()
            yield
        finally:
            await shutdown_mock()

    return _async_ctx


@pytest.fixture
def callable_async_ctx_partial(startup_mock: HookMock, shutdown_mock: HookMock) -> CallableAsyncCTX:
    @asynccontextmanager
    async def _async_ctx(app: Rapidy, test_arg: Any) -> AsyncGenerator[None, None]:
        try:
            await startup_mock()
            yield
        finally:
            await shutdown_mock()

    return partial(_async_ctx, test_arg=1)


@pytest.fixture
def async_ctx_manager(
    startup_mock: HookMock,
    shutdown_mock: HookMock,
) -> AbstractAsyncContextManager[Any]:
    @asynccontextmanager
    async def _async_ctx() -> AsyncGenerator[None, None]:
        try:
            await startup_mock()
            yield
        finally:
            await shutdown_mock()

    return _async_ctx()


async def test_lifespan_ctx_manager(
    app_client: AppClientFactory,
    startup_mock: HookMock,
    shutdown_mock: HookMock,
    async_ctx_manager: AbstractAsyncContextManager[Any],
) -> None:
    await _test_lifespan_manager(
        app_client=app_client,
        manager=async_ctx_manager,
        startup_mock=startup_mock,
        shutdown_mock=shutdown_mock,
    )


async def test_lifespan_partial_ctx_manager(
    app_client: AppClientFactory,
    startup_mock: HookMock,
    shutdown_mock: HookMock,
    callable_async_ctx_partial: CallableAsyncCTX,
) -> None:
    await _test_lifespan_manager(
        app_client=app_client,
        manager=callable_async_ctx_partial,
        startup_mock=startup_mock,
        shutdown_mock=shutdown_mock,
    )


async def test_lifespan_callable_async_ctx(
    app_client: AppClientFactory,
    startup_mock: HookMock,
    shutdown_mock: HookMock,
    callable_async_ctx: AbstractAsyncContextManager[Any],
) -> None:
    await _test_lifespan_manager(
        app_client=app_client,
        manager=callable_async_ctx,
        startup_mock=startup_mock,
        shutdown_mock=shutdown_mock,
    )


async def _test_lifespan_manager(
    app_client: AppClientFactory,
    manager: CallableAsyncCTX | AbstractAsyncContextManager[Any],
    startup_mock: HookMock,
    shutdown_mock: HookMock,
) -> None:
    app = Rapidy(lifespan=[manager])
    cli = await app_client(app)

    assert startup_mock.call_count == 1
    assert shutdown_mock.call_count == 0

    await cli.close()
    await asyncio.sleep(0.1)

    assert startup_mock.call_count == 1
    assert shutdown_mock.call_count == 1


async def test_lifespan_hooks(
    app_client: AppClientFactory,
    startup_mock: HookMock,
    shutdown_mock: HookMock,
    cleanup_mock: HookMock,
) -> None:
    app = Rapidy(on_startup=[startup_mock], on_shutdown=[shutdown_mock], on_cleanup=[cleanup_mock])
    cli = await app_client(app)

    assert startup_mock.call_count == 1
    assert shutdown_mock.call_count == 0
    assert cleanup_mock.call_count == 0

    await cli.close()
    await asyncio.sleep(0.1)

    assert startup_mock.call_count == 1
    assert shutdown_mock.call_count == 1
    assert cleanup_mock.call_count == 1


async def test_lifespan_startup_exception(app_client: AppClientFactory) -> None:
    async def hook() -> None:
        raise SomeError

    app = Rapidy(on_startup=[hook])

    with pytest.raises(SomeError):
        await app_client(app)


async def test_lifespan_shutdown_exception(app_client: AppClientFactory, shutdown_mock: HookMock) -> None:
    async def hook_with_exc() -> None:
        raise SomeError

    app = Rapidy(on_shutdown=[hook_with_exc, shutdown_mock])

    with pytest.raises(SomeError):  # noqa: PT012
        cli = await app_client(app)
        await cli.close()
        await asyncio.sleep(0.1)

    assert shutdown_mock.call_count == 1
