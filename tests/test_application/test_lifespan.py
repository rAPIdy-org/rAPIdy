import asyncio
from contextlib import asynccontextmanager
from functools import partial
from typing import Any, AsyncGenerator, TYPE_CHECKING, Union

import pytest
from pytest_aiohttp.plugin import AiohttpClient

from rapidy import web

if TYPE_CHECKING:
    from rapidy.lifespan import ABCAContextManager, CallableAsyncCTX


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
def callable_async_ctx(startup_mock: HookMock, shutdown_mock: HookMock) -> 'CallableAsyncCTX':
    @asynccontextmanager
    async def _async_ctx(app: web.Application) -> AsyncGenerator[None, None]:
        try:
            await startup_mock()
            yield
        finally:
            await shutdown_mock()

    return _async_ctx


@pytest.fixture
def callable_async_ctx_partial(startup_mock: HookMock, shutdown_mock: HookMock) -> 'CallableAsyncCTX':
    @asynccontextmanager
    async def _async_ctx(app: web.Application, test_arg: Any) -> AsyncGenerator[None, None]:
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
) -> 'ABCAContextManager':  # type: ignore[type-arg]
    @asynccontextmanager
    async def _async_ctx() -> AsyncGenerator[None, None]:
        try:
            await startup_mock()
            yield
        finally:
            await shutdown_mock()

    return _async_ctx()


async def test_lifespan_ctx_manager(
    aiohttp_client: AiohttpClient,
    startup_mock: HookMock,
    shutdown_mock: HookMock,
    async_ctx_manager: 'ABCAContextManager',  # type: ignore[type-arg]
) -> None:
    await _test_lifespan_manager(
        aiohttp_client=aiohttp_client,
        manager=async_ctx_manager,
        startup_mock=startup_mock,
        shutdown_mock=shutdown_mock,
    )


async def test_lifespan_partial_ctx_manager(
    aiohttp_client: AiohttpClient,
    startup_mock: HookMock,
    shutdown_mock: HookMock,
    callable_async_ctx_partial: 'CallableAsyncCTX',
) -> None:
    await _test_lifespan_manager(
        aiohttp_client=aiohttp_client,
        manager=callable_async_ctx_partial,
        startup_mock=startup_mock,
        shutdown_mock=shutdown_mock,
    )


async def test_lifespan_callable_async_ctx(
    aiohttp_client: AiohttpClient,
    startup_mock: HookMock,
    shutdown_mock: HookMock,
    callable_async_ctx: 'ABCAContextManager',  # type: ignore[type-arg]
) -> None:
    await _test_lifespan_manager(
        aiohttp_client=aiohttp_client,
        manager=callable_async_ctx,
        startup_mock=startup_mock,
        shutdown_mock=shutdown_mock,
    )


async def _test_lifespan_manager(
    aiohttp_client: AiohttpClient,
    manager: Union['CallableAsyncCTX', 'ABCAContextManager'],  # type: ignore[type-arg]
    startup_mock: HookMock,
    shutdown_mock: HookMock,
) -> None:
    app = web.Application(lifespan=[manager])
    cli = await aiohttp_client(app)

    assert startup_mock.call_count == 1
    assert shutdown_mock.call_count == 0

    await cli.close()
    await asyncio.sleep(0.1)

    assert startup_mock.call_count == 1
    assert shutdown_mock.call_count == 1


async def test_lifespan_hooks(
    aiohttp_client: AiohttpClient,
    startup_mock: HookMock,
    shutdown_mock: HookMock,
    cleanup_mock: HookMock,
) -> None:
    app = web.Application(on_startup=[startup_mock], on_shutdown=[shutdown_mock], on_cleanup=[cleanup_mock])
    cli = await aiohttp_client(app)

    assert startup_mock.call_count == 1
    assert shutdown_mock.call_count == 0
    assert cleanup_mock.call_count == 0

    await cli.close()
    await asyncio.sleep(0.1)

    assert startup_mock.call_count == 1
    assert shutdown_mock.call_count == 1
    assert cleanup_mock.call_count == 1


async def test_lifespan_startup_exception(aiohttp_client: AiohttpClient) -> None:
    async def hook() -> None:
        raise SomeError

    app = web.Application(on_startup=[hook])

    with pytest.raises(SomeError):
        await aiohttp_client(app)


async def test_lifespan_shutdown_exception(aiohttp_client: AiohttpClient, shutdown_mock: HookMock) -> None:
    async def hook_with_exc() -> None:
        raise SomeError

    app = web.Application(on_shutdown=[hook_with_exc, shutdown_mock])

    with pytest.raises(SomeError):  # noqa: PT012
        cli = await aiohttp_client(app)
        await cli.close()
        await asyncio.sleep(0.1)

    assert shutdown_mock.call_count == 1
