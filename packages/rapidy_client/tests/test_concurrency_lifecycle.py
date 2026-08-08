from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest
from rapidy_client import (
    ClientClosedError,
    Headers,
    HttpClient,
    Request,
    Response,
    ResponseExtensions,
    UpstreamConfig,
)


async def _body() -> AsyncIterator[bytes]:
    yield b"a"
    await asyncio.sleep(0)
    yield b"b"


class _BlockingTransport:
    def __init__(self) -> None:
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.requests: list[Request] = []

    async def handle(self, request: Request) -> Response:
        self.requests.append(request)
        self.entered.set()
        await self.release.wait()
        return Response(
            status=200,
            headers=Headers(),
            request=request,
            extensions=ResponseExtensions(
                elapsed=0.0,
                attempt=request.extensions.attempt,
            ),
        )

    async def aclose(self) -> None:
        return None


class _StreamingTransport(_BlockingTransport):
    async def handle(self, request: Request) -> Response:
        self.requests.append(request)
        return Response(
            status=200,
            headers=Headers(),
            request=request,
            extensions=ResponseExtensions(
                elapsed=0.0,
                attempt=request.extensions.attempt,
            ),
            stream=_body(),
        )


def _client(transport: _BlockingTransport) -> HttpClient:
    return HttpClient(
        UpstreamConfig.model_validate(
            {
                "base_url": "https://mock.test",
                "retry": {"max_attempts": 1},
                "log": {"level": "off"},
            }
        ),
        transport=transport,
    )


@pytest.mark.asyncio
async def test_close_drains_finite_request_and_rejects_new_work() -> None:
    transport = _BlockingTransport()
    client = _client(transport)
    request = asyncio.create_task(client.get("/finite"))
    await transport.entered.wait()
    closing = asyncio.create_task(client.aclose(drain_timeout=1.0))
    await asyncio.sleep(0)

    assert not closing.done()
    with pytest.raises(ClientClosedError):
        await client.get("/new")

    transport.release.set()
    assert (await request).status == 200
    await closing
    assert len(transport.requests) == 1


@pytest.mark.asyncio
async def test_request_cancellation_propagates_and_client_recovers() -> None:
    transport = _BlockingTransport()
    client = _client(transport)
    cancelled = asyncio.create_task(client.get("/cancelled"))
    await transport.entered.wait()
    cancelled.cancel()
    with pytest.raises(asyncio.CancelledError):
        await cancelled

    transport.release.set()
    assert (await client.get("/next")).status == 200
    await client.aclose()


@pytest.mark.asyncio
async def test_stream_response_allows_only_one_consumer() -> None:
    transport = _StreamingTransport()
    client = _client(transport)
    try:
        async with client.stream("GET", "/stream") as response:
            assert [chunk async for chunk in response.aiter_bytes(1)] == [b"a", b"b"]
            with pytest.raises(RuntimeError, match="already consumed"):
                await response.aread()
    finally:
        await client.aclose()


def test_client_cross_loop_affinity_is_enforced() -> None:
    transport = _BlockingTransport()
    transport.release.set()
    client = _client(transport)
    asyncio.run(client.get("/first"))

    with pytest.raises(RuntimeError, match="another event loop"):
        asyncio.run(client.get("/second"))

    asyncio.run(client.aclose())
