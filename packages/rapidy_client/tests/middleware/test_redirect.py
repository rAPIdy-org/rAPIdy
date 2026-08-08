from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from rapidy_client import (
    UNSET,
    URL,
    ContentFactory,
    Headers,
    RedirectConfig,
    RedirectNotAllowedError,
    Request,
    RequestExtensions,
    Response,
    ResponseExtensions,
    Timeout,
    TooManyRedirectsError,
)
from rapidy_client.middleware.redirect import RedirectMiddleware


async def _body(value: bytes = b"") -> AsyncIterator[bytes]:
    if value:
        yield value


def _request(
    *,
    method: str = "GET",
    url: str = "https://api.example.test/a",
    headers: Headers | None = None,
    content: Any = None,
    redirects: RedirectConfig | None = None,
) -> Request:
    return Request(
        method=method,
        url=URL(url),
        headers=headers or Headers(),
        content=content,
        extensions=RequestExtensions(
            upstream="catalog",
            endpoint="/a",
            request_id="request-1",
            timeout=Timeout(),
            retry=None,
            idempotent=method in {"GET", "HEAD"},
            auth_override=UNSET,
            deadline=123.0,
            redirects=redirects or RedirectConfig(),
            attempt=2,
        ),
    )


def _response(
    request: Request,
    status: int,
    *,
    location: str | None = None,
    on_close: Any = None,
) -> Response:
    headers = Headers({"Location": location}) if location is not None else Headers()
    return Response(
        status=status,
        headers=headers,
        request=request,
        extensions=ResponseExtensions(elapsed=0.0, attempt=2),
        stream=_body(),
        on_close=on_close,
    )


@pytest.mark.asyncio
async def test_no_follow_default_returns_3xx() -> None:
    calls: list[Request] = []

    async def call_next(request: Request) -> Response:
        calls.append(request)
        return _response(request, 302, location="/b")

    result = await RedirectMiddleware(allow_absolute_urls=False)(
        _request(), call_next
    )
    assert result.status == 302
    assert len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("location", ["/b", "https://api.example.test/b"])
async def test_follow_same_origin_location(location: str) -> None:
    calls: list[Request] = []

    async def call_next(request: Request) -> Response:
        calls.append(request)
        if len(calls) == 1:
            return _response(request, 302, location=location)
        return _response(request, 200)

    request = _request(redirects=RedirectConfig(follow=True))
    result = await RedirectMiddleware(allow_absolute_urls=False)(request, call_next)
    assert result.status == 200
    assert calls[1].url.path == "/b"
    assert calls[1].extensions is request.extensions


@pytest.mark.asyncio
async def test_cross_origin_blocked_default_closes_response() -> None:
    closes = 0

    async def close() -> None:
        nonlocal closes
        closes += 1

    async def call_next(request: Request) -> Response:
        return _response(
            request,
            302,
            location="https://evil.example.test/x",
            on_close=close,
        )

    request = _request(redirects=RedirectConfig(follow=True))
    with pytest.raises(RedirectNotAllowedError) as error:
        await RedirectMiddleware(allow_absolute_urls=False)(request, call_next)
    assert error.value.upstream == "catalog"
    assert closes == 1


@pytest.mark.asyncio
async def test_cross_origin_allowed_strips_secrets_and_host() -> None:
    calls: list[Request] = []

    async def call_next(request: Request) -> Response:
        calls.append(request)
        if len(calls) == 1:
            return _response(
                request, 302, location="https://other.example.test/x"
            )
        return _response(request, 200)

    request = _request(
        headers=Headers(
            {
                "Authorization": "secret",
                "Cookie": "sid=secret",
                "Proxy-Authorization": "proxy-secret",
                "Host": "api.example.test",
                "X-Safe": "yes",
            }
        ),
        redirects=RedirectConfig(follow=True),
    )
    await RedirectMiddleware(allow_absolute_urls=True)(request, call_next)
    redirected = calls[1]
    assert "authorization" not in redirected.headers
    assert "cookie" not in redirected.headers
    assert "proxy-authorization" not in redirected.headers
    assert "host" not in redirected.headers
    assert redirected.headers["x-safe"] == "yes"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("location", "strip_auth", "expected"),
    [("/b", True, "secret"), ("https://other.example.test/b", False, "secret")],
)
async def test_credentials_kept_when_policy_allows(
    location: str,
    strip_auth: bool,
    expected: str,
) -> None:
    calls: list[Request] = []

    async def call_next(request: Request) -> Response:
        calls.append(request)
        return (
            _response(request, 302, location=location)
            if len(calls) == 1
            else _response(request, 200)
        )

    request = _request(
        headers=Headers({"Authorization": "secret"}),
        redirects=RedirectConfig(
            follow=True,
            strip_auth_on_origin_change=strip_auth,
        ),
    )
    await RedirectMiddleware(allow_absolute_urls=True)(request, call_next)
    assert calls[1].headers["authorization"] == expected


@pytest.mark.asyncio
async def test_max_redirects_exceeded_raises_and_closes_last_response() -> None:
    calls: list[Request] = []
    closes = 0

    async def close() -> None:
        nonlocal closes
        closes += 1

    async def call_next(request: Request) -> Response:
        calls.append(request)
        return _response(request, 302, location=f"/hop-{len(calls)}", on_close=close)

    request = _request(redirects=RedirectConfig(follow=True))
    with pytest.raises(TooManyRedirectsError):
        await RedirectMiddleware(allow_absolute_urls=False)(request, call_next)
    assert len(calls) == 6
    assert closes == 6


@pytest.mark.asyncio
@pytest.mark.parametrize(("status", "expected"), [(301, "GET"), (302, "GET"), (303, "GET")])
async def test_post_redirect_to_get_drops_body_headers(
    status: int,
    expected: str,
) -> None:
    calls: list[Request] = []

    async def call_next(request: Request) -> Response:
        calls.append(request)
        return (
            _response(request, status, location="/b")
            if len(calls) == 1
            else _response(request, 200)
        )

    request = _request(
        method="POST",
        headers=Headers(
            {
                "Content-Length": "4",
                "Content-Type": "text/plain",
                "Content-Encoding": "gzip",
                "Transfer-Encoding": "chunked",
            }
        ),
        content=b"body",
        redirects=RedirectConfig(follow=True),
    )
    await RedirectMiddleware(allow_absolute_urls=False)(request, call_next)
    redirected = calls[1]
    assert redirected.method == expected
    assert redirected.content is None
    assert not any(name.casefold() in redirected.headers for name in (
        "content-length", "content-type", "content-encoding", "transfer-encoding"
    ))


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [307, 308])
async def test_307_308_preserve_method_and_replayable_body(status: int) -> None:
    calls: list[Request] = []
    content = ContentFactory(lambda: b"body")

    async def call_next(request: Request) -> Response:
        calls.append(request)
        return (
            _response(request, status, location="/b")
            if len(calls) == 1
            else _response(request, 200)
        )

    request = _request(
        method="POST",
        content=content,
        redirects=RedirectConfig(follow=True),
    )
    await RedirectMiddleware(allow_absolute_urls=False)(request, call_next)
    assert calls[1].method == "POST"
    assert calls[1].content is content


@pytest.mark.asyncio
async def test_head_303_stays_head() -> None:
    calls: list[Request] = []

    async def call_next(request: Request) -> Response:
        calls.append(request)
        return (
            _response(request, 303, location="/b")
            if len(calls) == 1
            else _response(request, 200)
        )

    request = _request(
        method="HEAD",
        redirects=RedirectConfig(follow=True),
    )
    await RedirectMiddleware(allow_absolute_urls=False)(request, call_next)
    assert calls[1].method == "HEAD"


@pytest.mark.asyncio
async def test_no_location_returns_response() -> None:
    async def call_next(request: Request) -> Response:
        return _response(request, 302)

    result = await RedirectMiddleware(allow_absolute_urls=False)(
        _request(redirects=RedirectConfig(follow=True)), call_next
    )
    assert result.status == 302


@pytest.mark.asyncio
async def test_max_response_size_stamped_on_response() -> None:
    async def call_next(request: Request) -> Response:
        return _response(request, 200)

    result = await RedirectMiddleware(
        allow_absolute_urls=False,
        max_response_size=16,
    )(_request(), call_next)
    assert result._max_response_size == 16
