from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import Annotated
from uuid import UUID

import pytest
from pydantic import BaseModel
from rapidy_client import (
    HttpClient,
    Response,
    Result,
    StatusError,
    UpstreamConfig,
    bind,
    get,
)
from rapidy_client.config import rapidy_client_request_id
from rapidy_client.observability import BaseObserver, RequestContext
from rapidy_client.schema import PathParam
from rapidy_client.testing import FakeClock, MockTransport


class Invoice(BaseModel):
    id: UUID
    amount: int


@get("/invoices/{invoice_id}", deadline=30.0)
async def get_invoice(
    invoice_id: Annotated[UUID, PathParam()],
) -> Invoice:
    raise NotImplementedError


@get("/invoice-result")
async def get_invoice_result() -> Result[Invoice]:
    raise NotImplementedError


@get("/invoice-result/{invoice_id}", statuses={404: None})
async def find_invoice_result(
    invoice_id: Annotated[UUID, PathParam()],
) -> Result[Invoice | None]:
    raise NotImplementedError


class _HookSpy(BaseObserver):
    def __init__(self) -> None:
        self.order: list[str] = []

    async def on_request_start(self, ctx: RequestContext) -> None:
        del ctx
        self.order.append("request_start")

    async def on_attempt_start(self, ctx: RequestContext) -> None:
        del ctx
        self.order.append("attempt_start")

    async def on_attempt_end(
        self,
        ctx: RequestContext,
        response: Response | None,
        exc: Exception | None,
    ) -> None:
        del ctx, response, exc
        self.order.append("attempt_end")

    async def on_request_end(
        self,
        ctx: RequestContext,
        response: Response,
    ) -> None:
        del ctx, response
        self.order.append("request_end")


def _client(mock: MockTransport, *, observer: BaseObserver | None = None) -> HttpClient:
    return HttpClient(
        UpstreamConfig.model_validate(
            {
                "base_url": "https://mock.test",
                "retry": {"max_attempts": 1},
                "log": {"level": "off"},
            }
        ),
        name="billing",
        transport=mock,
        observers=() if observer is None else (observer,),
        _clock=FakeClock(),
    )


@pytest.mark.asyncio
async def test_happy_path_full_trace() -> None:
    uid = UUID("00000000-0000-0000-0000-000000000007")
    mock = MockTransport()
    mock.route("GET", f"/invoices/{uid}").respond(
        json={"id": str(uid), "amount": 100},
        headers={"x-source": "golden"},
    )
    spy = _HookSpy()
    client = _client(mock, observer=spy)
    token = rapidy_client_request_id.set("rid-happy-1")
    try:
        invoice = await bind(get_invoice, client)(invoice_id=uid)
    finally:
        rapidy_client_request_id.reset(token)
        await client.aclose()

    call = mock.calls[-1]
    request = call.request
    response = call.response

    assert request.method == "GET"
    assert request.url.path == f"/invoices/{uid}"
    assert request.extensions.upstream == "billing"
    assert request.extensions.endpoint == "/invoices/{invoice_id}"
    assert request.extensions.attempt == 1
    assert request.extensions.idempotent is True

    assert request.headers["x-request-id"] == "rid-happy-1"
    assert int(request.headers["x-rapidy-deadline-ms"]) > 0
    assert "authorization" not in request.headers
    assert "traceparent" not in request.headers

    assert response is not None
    assert response.status == 200
    assert response.extensions.attempt == 1
    assert hasattr(response.extensions, "connection_reused")
    assert hasattr(response.extensions, "pool_wait")
    assert response.is_success

    assert invoice == Invoice(id=uid, amount=100)
    assert spy.order == [
        "request_start",
        "request_end",
    ]
    mock.assert_called("GET", f"/invoices/{uid}", times=1)


@pytest.mark.asyncio
async def test_result_success_preserves_status_headers_and_is_frozen() -> None:
    uid = UUID("00000000-0000-0000-0000-000000000008")
    mock = MockTransport()
    mock.route("GET", "/invoice-result").respond(
        json={"id": str(uid), "amount": 250},
        headers={"x-trace": "trace-8"},
    )
    client = _client(mock)
    try:
        result = await bind(get_invoice_result, client)()
    finally:
        await client.aclose()

    assert result.value == Invoice(id=uid, amount=250)
    assert result.status == 200
    assert result.headers["x-trace"] == "trace-8"
    with pytest.raises(FrozenInstanceError):
        result.status = 201  # type: ignore[misc]


@pytest.mark.asyncio
async def test_result_declared_status_is_a_value() -> None:
    uid = UUID("00000000-0000-0000-0000-000000000009")
    mock = MockTransport()
    mock.route("GET", f"/invoice-result/{uid}").respond(
        status=404,
        headers={"x-trace": "not-found"},
    )
    client = _client(mock)
    try:
        result = await bind(find_invoice_result, client)(invoice_id=uid)
    finally:
        await client.aclose()

    assert result.value is None
    assert result.status == 404
    assert result.headers["x-trace"] == "not-found"


@pytest.mark.asyncio
async def test_result_undeclared_status_still_raises() -> None:
    mock = MockTransport()
    mock.route("GET", "/invoice-result").respond(status=503, text="unavailable")
    client = _client(mock)
    try:
        with pytest.raises(StatusError) as captured:
            await bind(get_invoice_result, client)()
    finally:
        await client.aclose()

    assert captured.value.status == 503
