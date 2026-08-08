from __future__ import annotations

import pytest
from rapidy_client import (
    HttpClient,
    HttpTimeoutError,
    ProtocolError,
    UpstreamConfig,
)
from rapidy_client.testing.chaos import ChaosServer


def _config(base_url: str, *, read_timeout: float = 5.0) -> UpstreamConfig:
    return UpstreamConfig.model_validate(
        {
            "base_url": base_url,
            "timeout": {"read": read_timeout},
            "retry": {"max_attempts": 1},
            "log": {"level": "off"},
        }
    )


@pytest.mark.asyncio
async def test_real_client_reuses_keepalive_connection() -> None:
    async with ChaosServer().respond_ok(body=b"loopback") as server:
        client = HttpClient(_config(server.url), name="chaos")
        try:
            first = await client.get("/")
            second = await client.get("/")
        finally:
            await client.aclose()

    assert await first.aread() == b"loopback"
    assert await second.aread() == b"loopback"
    assert first.extensions.connection_reused is False
    assert second.extensions.connection_reused is True


@pytest.mark.asyncio
async def test_real_client_maps_mid_body_disconnect() -> None:
    async with ChaosServer().disconnect_after(10) as server:
        client = HttpClient(_config(server.url), name="chaos")
        try:
            with pytest.raises(ProtocolError):
                await client.get("/")
        finally:
            await client.aclose()


@pytest.mark.asyncio
async def test_real_client_preserves_read_timeout_phase() -> None:
    async with ChaosServer().freeze(0.2) as server:
        client = HttpClient(_config(server.url, read_timeout=0.04), name="chaos")
        try:
            with pytest.raises(HttpTimeoutError) as captured:
                await client.get("/")
        finally:
            await client.aclose()

    assert captured.value.phase == "read"
