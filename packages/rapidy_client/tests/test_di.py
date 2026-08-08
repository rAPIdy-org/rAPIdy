from __future__ import annotations

from typing import Annotated, Any

import pytest
from rapidy_client import HttpClient, Response, SchemaDefinitionError, UpstreamConfig
from rapidy_client.di import (
    HttpApp,
    RapidyClientProvider,
    provide_controller,
    provide_upstream,
)
from rapidy_client.schema import QueryParam, controller, get
from rapidy_core.di import Component, make_async_container

BILLING = Component("billing")
ORDERS = Component("orders")


@controller("/billing")
class BillingApi:
    @get("/health")
    async def health(self) -> Response:
        raise NotImplementedError


@get("/health")
async def health_endpoint() -> Response:
    raise NotImplementedError


class HealthEndpointKey:
    pass


@controller("/broken")
class BrokenApi:
    @get("/value")
    async def value(
        self,
        missing: Annotated[MissingDependency, QueryParam()],  # type: ignore[name-defined]  # noqa: F821
    ) -> Response:
        raise NotImplementedError


def _config(base_url: str = "https://example.test") -> UpstreamConfig:
    return UpstreamConfig.model_validate(
        {
            "base_url": base_url,
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


@pytest.mark.asyncio
async def test_provide_controller_uses_qualified_component() -> None:
    upstream = provide_upstream(BILLING, _config())
    controller_provider = provide_controller(BillingApi, component=BILLING)

    async with make_async_container(upstream, controller_provider) as container:
        client = await container.get(HttpClient, component=BILLING)
        api = await container.get(BillingApi)

        assert isinstance(api, BillingApi)
        assert cast_any(api)._rapidy_client is client


@pytest.mark.asyncio
async def test_provide_endpoint_binds_under_explicit_key() -> None:
    providers = (
        RapidyClientProvider.upstream(BILLING, _config()),
        RapidyClientProvider.endpoint(
            health_endpoint,
            provides=HealthEndpointKey,
            component=BILLING,
        ),
    )

    async with make_async_container(*providers) as container:
        endpoint = await container.get(HealthEndpointKey)
        client = await container.get(HttpClient, component=BILLING)

        assert callable(endpoint)
        assert cast_any(endpoint)._client is client


@pytest.mark.asyncio
async def test_http_app_two_components_and_close_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closes: dict[int, int] = {}
    original = HttpClient.aclose

    async def tracked_close(
        self: HttpClient,
        *,
        drain_timeout: float = 10.0,
    ) -> None:
        closes[id(self)] = closes.get(id(self), 0) + 1
        await original(self, drain_timeout=drain_timeout)

    monkeypatch.setattr(HttpClient, "aclose", tracked_close)
    app = HttpApp(
        upstreams={
            BILLING: _config("https://billing.example.test"),
            ORDERS: _config("https://orders.example.test"),
        },
        controllers={BillingApi: BILLING},
    )

    async with app:
        billing = await app.container.get(HttpClient, component=BILLING)
        orders = await app.container.get(HttpClient, component=ORDERS)
        api = await app.controller(BillingApi)

        assert billing is not orders
        assert cast_any(api)._rapidy_client is billing
        assert closes == {}

    assert closes == {id(billing): 1, id(orders): 1}
    with pytest.raises(RuntimeError, match="not entered"):
        _ = app.container


@pytest.mark.asyncio
async def test_http_app_access_and_double_enter_guards() -> None:
    app = HttpApp(upstreams={BILLING: _config()})
    with pytest.raises(RuntimeError, match="not entered"):
        _ = app.container

    await app.__aenter__()
    try:
        with pytest.raises(RuntimeError, match="twice"):
            await app.__aenter__()
        with pytest.raises(LookupError, match="not registered"):
            await app.controller(BillingApi)
    finally:
        await app.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_http_app_startup_fails_fast_and_closes_client(
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
    app = HttpApp(
        upstreams={BILLING: _config()},
        controllers={BrokenApi: BILLING},
    )

    with pytest.raises(SchemaDefinitionError, match="BrokenApi.value"):
        await app.__aenter__()

    assert closes == 1
    with pytest.raises(RuntimeError, match="not entered"):
        _ = app.container


def cast_any(value: object) -> Any:
    return value
