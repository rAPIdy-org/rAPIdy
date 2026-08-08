from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import TYPE_CHECKING

import pytest
from rapidy_client import HttpClient
from rapidy_client._models import (
    URL,
    BaseTransport,
    Headers,
    Request,
    RequestExtensions,
    Response,
    ResponseExtensions,
    Timeout,
)
from rapidy_client.config import RedirectConfig
from rapidy_client.errors import ConnectError
from rapidy_client.testing import MockRouteError, MockTransport, RecordedCall
from rapidy_core import UNSET

if TYPE_CHECKING:
    from rapidy_client.testing.plugin import HttpClientFactory


def _make_request(method: str, path: str, *, attempt: int = 0) -> Request:
    extensions = RequestExtensions(
        upstream="mock",
        endpoint=path,
        request_id=None,
        timeout=Timeout(),
        retry=None,
        idempotent=False,
        auth_override=UNSET,
        deadline=None,
        redirects=RedirectConfig(),
        attempt=attempt,
    )
    return Request(
        method=method,
        url=URL(f"https://mock.test{path}"),
        headers=Headers(),
        content=None,
        extensions=extensions,
    )


def _make_response(request: Request, *, status: int) -> Response:
    return Response(
        status=status,
        headers=Headers(),
        request=request,
        extensions=ResponseExtensions(
            elapsed=0.0,
            attempt=request.extensions.attempt,
        ),
    )


def test_mock_transport_satisfies_base_transport() -> None:
    assert isinstance(MockTransport(), BaseTransport)


@pytest.mark.asyncio
async def test_route_static_path_via_client(
    http_client_factory: HttpClientFactory,
    mock_transport: MockTransport,
) -> None:
    mock_transport.route("GET", "/ping").respond(status=200)
    client = http_client_factory()

    response = await client.get("/ping")

    assert response.status == 200
    mock_transport.assert_called("GET", "/ping", times=1)


@pytest.mark.asyncio
async def test_route_path_param(
    http_client_factory: HttpClientFactory,
    mock_transport: MockTransport,
) -> None:
    mock_transport.route("GET", "/users/{id}").respond(json={"id": 42})

    response = await http_client_factory().get("/users/42")

    assert response.status == 200
    assert await response.json() == {"id": 42}
    mock_transport.assert_called("GET", "/users/{id}", times=1)


@pytest.mark.asyncio
async def test_route_ignores_query_and_method_case() -> None:
    mock = MockTransport()
    mock.route("get", "/items").respond(status=204)

    response = await mock.handle(_make_request("GET", "/items?limit=1"))

    assert response.status == 204


@pytest.mark.asyncio
async def test_unmatched_route_raises_with_registry() -> None:
    mock = MockTransport()
    mock.route("GET", "/a").respond()
    mock.route("POST", "/b").respond()

    with pytest.raises(MockRouteError) as captured:
        await mock.handle(_make_request("GET", "/c"))

    error = captured.value
    assert error.registered == ["GET /a", "POST /b"]
    assert "GET /a" in str(error)
    assert "POST /b" in str(error)
    assert "GET /c" in str(error)
    assert mock.calls[-1].exception is error


@pytest.mark.asyncio
async def test_times_then_raise_sequence() -> None:
    mock = MockTransport()
    error = ConnectError("boom")
    mock.route("GET", "/flaky").times(2).raise_(error).then().respond(status=200)

    for _ in range(2):
        with pytest.raises(ConnectError, match="boom"):
            await mock.handle(_make_request("GET", "/flaky"))

    assert (await mock.handle(_make_request("GET", "/flaky"))).status == 200
    assert (await mock.handle(_make_request("GET", "/flaky"))).status == 200


@pytest.mark.asyncio
async def test_respond_with_handler_receives_request() -> None:
    mock = MockTransport()
    seen: list[Request] = []

    async def handler(request: Request) -> Response:
        seen.append(request)
        return _make_response(request, status=201)

    mock.route("POST", "/orders").respond_with(handler)
    request = _make_request("POST", "/orders")

    response = await mock.handle(request)

    assert response.status == 201
    assert seen == [request]


@pytest.mark.asyncio
async def test_respond_json_null_and_explicit_content_type() -> None:
    mock = MockTransport()
    mock.route("GET", "/null").respond(
        json=None,
        headers={"Content-Type": "application/problem+json"},
    )

    response = await mock.handle(_make_request("GET", "/null"))

    assert await response.json() is None
    assert response.headers.get_all("content-type") == ["application/problem+json"]


@pytest.mark.asyncio
async def test_calls_records_response_and_exception() -> None:
    mock = MockTransport()
    error = ConnectError("unavailable")
    mock.route("GET", "/ok").respond(status=204)
    mock.route("GET", "/fail").raise_(error)

    response = await mock.handle(_make_request("GET", "/ok"))
    with pytest.raises(ConnectError):
        await mock.handle(_make_request("GET", "/fail"))

    assert mock.calls[0].response is response
    assert mock.calls[0].exception is None
    assert mock.calls[1].response is None
    assert mock.calls[1].exception is error


def test_recorded_call_is_immutable() -> None:
    call = RecordedCall(request=_make_request("GET", "/x"))

    with pytest.raises(FrozenInstanceError):
        call.response = None  # type: ignore[misc]


@pytest.mark.asyncio
async def test_assert_called_default_and_exact_count() -> None:
    mock = MockTransport()
    mock.route("GET", "/users/{id}").respond()

    with pytest.raises(AssertionError, match="at least once"):
        mock.assert_called("GET", "/users/{id}")

    await mock.handle(_make_request("GET", "/users/1"))
    mock.assert_called("get", "/users/{id}")
    mock.assert_called("GET", "/users/{id}", times=1)
    with pytest.raises(AssertionError, match="got 1"):
        mock.assert_called("GET", "/users/{id}", times=2)


@pytest.mark.asyncio
async def test_first_match_wins() -> None:
    mock = MockTransport()
    mock.route("GET", "/x").respond(status=200)
    mock.route("GET", "/x").respond(status=500)

    assert (await mock.handle(_make_request("GET", "/x"))).status == 200


@pytest.mark.asyncio
async def test_route_no_outcome_raises_runtime_error() -> None:
    mock = MockTransport()
    mock.route("GET", "/empty")

    with pytest.raises(RuntimeError, match="no outcome"):
        await mock.handle(_make_request("GET", "/empty"))


@pytest.mark.parametrize("count", [0, -1])
def test_times_non_positive_rejected(count: int) -> None:
    with pytest.raises(ValueError, match="n >= 1"):
        MockTransport().route("GET", "/x").times(count)


@pytest.mark.asyncio
async def test_mock_not_closed_by_client(
    http_client_factory: HttpClientFactory,
) -> None:
    mock = MockTransport()
    client = http_client_factory(transport=mock)

    assert client._owns_transport is False
    await client.aclose()
    assert mock.closed is False


@pytest.mark.asyncio
async def test_owns_transport_flag_false_for_external_mock(
    http_client_factory: HttpClientFactory,
) -> None:
    client = http_client_factory(transport=MockTransport())

    assert isinstance(client, HttpClient)
    assert client._owns_transport is False
