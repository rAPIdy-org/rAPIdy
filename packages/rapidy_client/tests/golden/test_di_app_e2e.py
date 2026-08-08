from __future__ import annotations

from typing import Annotated, Any

import pytest
from pydantic import BaseModel
from rapidy_client import HttpClient, Response, UpstreamConfig
from rapidy_client.di import HttpApp, provide_endpoint
from rapidy_client.schema import PathParam, controller, get
from rapidy_client.testing import MockTransport
from rapidy_core.di import Component

BILLING = Component("billing")
AUDIT = Component("audit")


class Invoice(BaseModel):
    id: int


@controller("/billing")
class BillingApi:
    @get("/invoices/{invoice_id}")
    async def invoice(
        self,
        invoice_id: Annotated[int, PathParam()],
    ) -> Invoice:
        raise NotImplementedError


@get("/events/{event_id}")
async def audit_event(
    event_id: Annotated[int, PathParam()],
) -> Response:
    raise NotImplementedError


class AuditEndpoint:
    pass


def _config(base_url: str) -> UpstreamConfig:
    return UpstreamConfig.model_validate(
        {"base_url": base_url, "retry": {"max_attempts": 1}, "log": {"level": "off"}}
    )


def _install_mock_clients(
    monkeypatch: pytest.MonkeyPatch,
    transports: dict[str, MockTransport],
    closes: dict[int, int],
) -> None:
    original_init = HttpClient.__init__
    original_close = HttpClient.aclose

    def mock_init(
        self: HttpClient,
        config: UpstreamConfig,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        kwargs["transport"] = transports[str(config.base_url)]
        original_init(self, config, *args, **kwargs)

    async def tracked_close(
        self: HttpClient,
        *,
        drain_timeout: float = 10.0,
    ) -> None:
        closes[id(self)] = closes.get(id(self), 0) + 1
        await original_close(self, drain_timeout=drain_timeout)

    monkeypatch.setattr(HttpClient, "__init__", mock_init)
    monkeypatch.setattr(HttpClient, "aclose", tracked_close)


@pytest.mark.asyncio
async def test_http_app_components_execute_and_close_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    billing_mock = MockTransport()
    billing_mock.route("GET", "/billing/invoices/7").respond(json={"id": 7})
    audit_mock = MockTransport()
    audit_mock.route("GET", "/events/9").respond(status=204)
    closes: dict[int, int] = {}
    _install_mock_clients(
        monkeypatch,
        {
            "https://billing.test/": billing_mock,
            "https://audit.test/": audit_mock,
        },
        closes,
    )
    app = HttpApp(
        upstreams={
            BILLING: _config("https://billing.test"),
            AUDIT: _config("https://audit.test"),
        },
        controllers={BillingApi: BILLING},
        di_providers=(
            provide_endpoint(audit_event, provides=AuditEndpoint, component=AUDIT),
        ),
    )

    async with app:
        billing = await app.container.get(HttpClient, component=BILLING)
        audit = await app.container.get(HttpClient, component=AUDIT)
        assert billing is await app.container.get(HttpClient, component=BILLING)
        assert audit is await app.container.get(HttpClient, component=AUDIT)
        assert billing is not audit

        api = await app.controller(BillingApi)
        assert await api.invoice(7) == Invoice(id=7)
        endpoint = await app.container.get(AuditEndpoint)
        assert (await endpoint(9)).status == 204

    assert closes == {id(billing): 1, id(audit): 1}
    billing_mock.assert_called("GET", "/billing/invoices/7", times=1)
    audit_mock.assert_called("GET", "/events/9", times=1)


@pytest.mark.asyncio
async def test_http_app_exception_still_finalizes_every_component(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closes: dict[int, int] = {}
    _install_mock_clients(
        monkeypatch,
        {
            "https://billing.test/": MockTransport(),
            "https://audit.test/": MockTransport(),
        },
        closes,
    )
    app = HttpApp(
        upstreams={
            BILLING: _config("https://billing.test"),
            AUDIT: _config("https://audit.test"),
        }
    )

    with pytest.raises(RuntimeError, match="application failed"):
        async with app:
            billing = await app.container.get(HttpClient, component=BILLING)
            audit = await app.container.get(HttpClient, component=AUDIT)
            raise RuntimeError("application failed")

    assert closes == {id(billing): 1, id(audit): 1}
