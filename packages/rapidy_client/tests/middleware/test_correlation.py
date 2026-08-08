from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from rapidy_client import (
    UNSET,
    URL,
    Headers,
    RedirectConfig,
    Request,
    RequestExtensions,
    Response,
    ResponseExtensions,
    Timeout,
)
from rapidy_client.errors import ConnectError
from rapidy_client.middleware.correlation import CorrelationMiddleware


async def _body() -> AsyncIterator[bytes]:
    yield b"ok"


def _request(request_id: str | None, *, headers: Headers | None = None) -> Request:
    return Request(
        method="POST",
        url=URL("https://example.test/x"),
        headers=headers or Headers(),
        content=b"body",
        extensions=RequestExtensions(
            upstream="catalog",
            endpoint="/x",
            request_id=request_id,
            timeout=Timeout(),
            retry=None,
            idempotent=False,
            auth_override=UNSET,
            deadline=None,
            redirects=RedirectConfig(),
        ),
    )


def _response(request: Request) -> Response:
    return Response(
        status=200,
        headers=Headers(),
        request=request,
        extensions=ResponseExtensions(elapsed=0.0, attempt=0),
        stream=_body(),
    )


@pytest.mark.asyncio
async def test_injects_request_id_from_extensions() -> None:
    seen: list[Request] = []

    async def call_next(request: Request) -> Response:
        seen.append(request)
        return _response(request)

    await CorrelationMiddleware()(_request("rid-1"), call_next)
    assert seen[0].headers["x-request-id"] == "rid-1"


@pytest.mark.asyncio
@pytest.mark.parametrize("request_id", [None, ""])
async def test_empty_request_id_does_not_add_header(
    request_id: str | None,
) -> None:
    seen: list[Request] = []

    async def call_next(request: Request) -> Response:
        seen.append(request)
        return _response(request)

    request = _request(request_id)
    await CorrelationMiddleware()(request, call_next)
    assert "x-request-id" not in seen[0].headers
    assert seen[0] is request


@pytest.mark.asyncio
async def test_replaces_incoming_request_id_without_duplicate() -> None:
    seen: list[Request] = []

    async def call_next(request: Request) -> Response:
        seen.append(request)
        return _response(request)

    request = _request(
        "rid-2",
        headers=Headers([("X-Request-ID", "stale"), ("x-request-id", "also-stale")]),
    )
    await CorrelationMiddleware()(request, call_next)
    assert seen[0].headers.get_all("x-request-id") == ["rid-2"]


@pytest.mark.asyncio
async def test_preserves_order_content_extensions_and_original_request() -> None:
    seen: list[Request] = []

    async def call_next(request: Request) -> Response:
        seen.append(request)
        return _response(request)

    original = _request("rid", headers=Headers([("A", "1"), ("B", "2")]))
    await CorrelationMiddleware()(original, call_next)
    correlated = seen[0]
    assert correlated is not original
    assert "x-request-id" not in original.headers
    assert correlated.headers.multi_items() == [
        ("A", "1"),
        ("B", "2"),
        ("X-Request-ID", "rid"),
    ]
    assert correlated.content is original.content
    assert correlated.extensions is original.extensions


@pytest.mark.asyncio
async def test_propagates_result_and_exception() -> None:
    request = _request("rid")

    async def success(correlated: Request) -> Response:
        return _response(correlated)

    result = await CorrelationMiddleware()(request, success)
    assert result.status == 200

    async def failure(correlated: Request) -> Response:
        del correlated
        raise ConnectError("boom")

    with pytest.raises(ConnectError):
        await CorrelationMiddleware()(request, failure)
