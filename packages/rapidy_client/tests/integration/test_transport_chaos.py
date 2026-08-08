import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from rapidy_client import (
    UNSET,
    URL,
    Headers,
    HttpTimeoutError,
    ProtocolError,
    Request,
    RequestExtensions,
    ServerDisconnectedError,
    Timeout,
)
from rapidy_client.testing.chaos import ChaosServer
from rapidy_client.transports import HttpxTransport
from rapidy_client.transports.httpx import map_transport_exception


@dataclass(slots=True)
class PoolLimits:
    max_connections: int = 10
    max_per_host: int = 2
    keepalive_timeout: float = 15.0
    force_close: bool = False


@dataclass(slots=True)
class TLSConfig:
    verify: bool = False
    ca_file: Path | None = None
    min_version: str = "TLSv1_2"
    client_cert: Path | None = None
    client_key: Path | None = None


def _transport(
    base_url: str,
    *,
    max_per_host: int = 2,
) -> HttpxTransport:
    return HttpxTransport(
        base_url=base_url,
        limits=PoolLimits(max_per_host=max_per_host),  # type: ignore[arg-type]
        tls=TLSConfig(),  # type: ignore[arg-type]
    )


def _request(
    url: str,
    *,
    timeout: Timeout | None = None,
    content: bytes | AsyncIterator[bytes] | None = None,
) -> Request:
    return Request(
        method="POST" if content is not None else "GET",
        url=URL(url),
        headers=Headers(),
        content=content,
        extensions=RequestExtensions(
            upstream="chaos",
            endpoint="/",
            request_id="integration-1",
            timeout=timeout or Timeout(),
            retry=None,
            idempotent=True,
            auth_override=UNSET,
            deadline=None,
            redirects=None,  # type: ignore[arg-type]
        ),
    )


@pytest.mark.asyncio
async def test_keepalive_reuse() -> None:
    async with ChaosServer().respond_ok(body=b"ok") as server:
        transport = _transport(server.url)
        try:
            first = await transport.handle(_request(server.url))
            assert await first.aread() == b"ok"
            assert first.extensions.connection_reused is False

            second = await transport.handle(_request(server.url))
            assert await second.aread() == b"ok"
            assert second.extensions.connection_reused is True
        finally:
            await transport.aclose()


@pytest.mark.asyncio
async def test_disconnect_on_reused_maps_server_disconnected() -> None:
    async with ChaosServer().reset_on_reuse() as server:
        transport = _transport(server.url)
        try:
            first = await transport.handle(_request(server.url))
            await first.aread()
            with pytest.raises(ServerDisconnectedError):
                await transport.handle(_request(server.url))
        finally:
            await transport.aclose()


@pytest.mark.asyncio
async def test_mid_body_disconnect_maps_protocol() -> None:
    async with ChaosServer().disconnect_after(10) as server:
        transport = _transport(server.url)
        try:
            response = await transport.handle(_request(server.url))
            with pytest.raises(ProtocolError):
                await response.aread()
        finally:
            await transport.aclose()


@pytest.mark.asyncio
async def test_phase_read_via_freeze() -> None:
    async with ChaosServer().freeze(0.2) as server:
        transport = _transport(server.url)
        try:
            with pytest.raises(HttpTimeoutError) as error:
                await transport.handle(_request(server.url, timeout=Timeout(read=0.04)))
            assert error.value.phase == "read"
        finally:
            await transport.aclose()


@pytest.mark.asyncio
async def test_phase_pool_via_semaphore() -> None:
    async with ChaosServer().freeze(0.3) as server:
        transport = _transport(server.url, max_per_host=1)
        first = asyncio.create_task(
            transport.handle(_request(server.url, timeout=Timeout(read=1.0, pool=1.0)))
        )
        try:
            await asyncio.sleep(0.03)
            with pytest.raises(HttpTimeoutError) as error:
                await transport.handle(_request(server.url, timeout=Timeout(pool=0.04)))
            assert error.value.phase == "pool"
        finally:
            first.cancel()
            await asyncio.gather(first, return_exceptions=True)
            await transport.aclose()


@pytest.mark.asyncio
async def test_phase_total_via_attempt_wrapper() -> None:
    async with ChaosServer().slow_body(100) as server:
        transport = _transport(server.url)
        try:
            response = await transport.handle(_request(server.url))
            with pytest.raises(TimeoutError) as source:
                async with asyncio.timeout(0.04):
                    await response.aread()
            mapped = map_transport_exception(source.value)
            assert isinstance(mapped, HttpTimeoutError)
            assert mapped.phase == "total"
        finally:
            await transport.aclose()


@pytest.mark.asyncio
async def test_phase_write_via_stall() -> None:
    chunk = b"x" * (1024 * 1024)

    async def large_body() -> AsyncIterator[bytes]:
        for _ in range(128):
            yield chunk

    async with ChaosServer().stall_request_read(0.3) as server:
        transport = _transport(server.url)
        try:
            with pytest.raises(HttpTimeoutError) as error:
                await transport.handle(
                    _request(
                        server.url,
                        timeout=Timeout(write=0.02, read=1.0),
                        content=large_body(),
                    )
                )
            assert error.value.phase == "write"
        finally:
            await transport.aclose()


@pytest.mark.asyncio
async def test_phase_connect_distinguishable() -> None:
    async with ChaosServer().freeze(0.3) as server:
        secure_url = f"https://{server.host}:{server.port}"
        transport = _transport(secure_url)
        try:
            with pytest.raises(HttpTimeoutError) as error:
                await transport.handle(
                    _request(
                        secure_url,
                        timeout=Timeout(connect=0.04, read=1.0),
                    )
                )
            assert error.value.phase == "connect"
        finally:
            await transport.aclose()


@pytest.mark.asyncio
async def test_retry_after_response_passthrough() -> None:
    async with ChaosServer().retry_after("1", status=503) as server:
        transport = _transport(server.url)
        try:
            response = await transport.handle(_request(server.url))
            assert response.status == 503
            assert response.headers.get("retry-after") == "1"
            assert await response.aread() == b"retry later"
        finally:
            await transport.aclose()
