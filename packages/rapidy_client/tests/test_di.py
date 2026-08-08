from __future__ import annotations

import pytest
from rapidy_client import HttpClient, UpstreamConfig
from rapidy_client.di import provide_upstream
from rapidy_core.di import make_async_container


def _config() -> UpstreamConfig:
    return UpstreamConfig.model_validate(
        {
            "base_url": "https://example.test",
            "log": {"level": "off"},
        }
    )


@pytest.mark.asyncio
async def test_provide_upstream_is_component_app_singleton_and_closes_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closes = 0
    original = HttpClient.aclose

    async def tracked_close(
        self: HttpClient,
        *,
        drain_timeout: float = 10.0,
    ) -> None:
        nonlocal closes
        closes += 1
        await original(self, drain_timeout=drain_timeout)

    monkeypatch.setattr(HttpClient, "aclose", tracked_close)
    provider = provide_upstream("catalog", _config())
    assert provider.component == "catalog"

    async with make_async_container(provider) as container:
        first = await container.get(HttpClient, component="catalog")
        second = await container.get(HttpClient, component="catalog")
        assert first is second
        assert first._name == "catalog"
        assert closes == 0
    assert closes == 1


@pytest.mark.asyncio
async def test_provide_upstream_closes_once_when_scope_exits_with_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closes = 0
    original = HttpClient.aclose

    async def tracked_close(
        self: HttpClient,
        *,
        drain_timeout: float = 10.0,
    ) -> None:
        nonlocal closes
        closes += 1
        await original(self, drain_timeout=drain_timeout)

    monkeypatch.setattr(HttpClient, "aclose", tracked_close)
    provider = provide_upstream("catalog", _config())

    with pytest.raises(RuntimeError, match="scope failed"):
        async with make_async_container(provider) as container:
            await container.get(HttpClient, component="catalog")
            raise RuntimeError("scope failed")
    assert closes == 1
