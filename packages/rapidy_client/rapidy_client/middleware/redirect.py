from __future__ import annotations

from typing import ClassVar, TypedDict

from rapidy_client._models import CallNext, Headers, Request, Response
from rapidy_client.config import RedirectConfig
from rapidy_client.errors import RedirectNotAllowedError, TooManyRedirectsError

_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_SECRET_HEADERS = frozenset(
    {"authorization", "cookie", "proxy-authorization"}
)
_BODY_HEADERS = frozenset(
    {"content-length", "content-type", "content-encoding", "transfer-encoding"}
)


class _ErrorContext(TypedDict):
    upstream: str | None
    endpoint: str | None
    request_id: str | None


def _error_context(request: Request) -> _ErrorContext:
    extensions = request.extensions
    return {
        "upstream": extensions.upstream,
        "endpoint": extensions.endpoint,
        "request_id": extensions.request_id,
    }


def _redirect_method(request: Request, status: int) -> str:
    if status == 303 and request.method != "HEAD":
        return "GET"
    if status in {301, 302} and request.method == "POST":
        return "GET"
    return request.method


def _rewrite_headers(
    headers: Headers,
    *,
    origin_changed: bool,
    strip_auth: bool,
    method_changed: bool,
) -> Headers:
    drop: set[str] = set()
    if origin_changed and strip_auth:
        drop.update(_SECRET_HEADERS)
    if origin_changed:
        drop.add("host")
    if method_changed:
        drop.update(_BODY_HEADERS)
    return Headers(
        (name, value)
        for name, value in headers.multi_items()
        if name.casefold() not in drop
    )


class RedirectMiddleware:
    """Follow redirects at the innermost middleware layer with SSRF guards."""

    handshake_safe: ClassVar[bool] = False

    def __init__(
        self,
        *,
        allow_absolute_urls: bool,
        max_response_size: int | None = None,
    ) -> None:
        self._allow_absolute_urls = allow_absolute_urls
        self._max_response_size = max_response_size

    async def __call__(self, request: Request, call_next: CallNext) -> Response:
        config: RedirectConfig = request.extensions.redirects
        current = request
        hops = 0

        while True:
            response = await call_next(current)
            response._max_response_size = self._max_response_size
            if not config.follow or response.status not in _REDIRECT_STATUSES:
                return response

            location = response.headers.get("location")
            if location is None:
                return response
            if hops >= config.max_redirects:
                await response.aclose()
                raise TooManyRedirectsError(
                    f"exceeded max_redirects={config.max_redirects}",
                    **_error_context(current),
                )

            target = current.url.join(location)
            origin_changed = target.origin() != current.url.origin()
            if origin_changed and not self._allow_absolute_urls:
                await response.aclose()
                raise RedirectNotAllowedError(
                    "cross-origin redirect "
                    f"to {target!r} blocked (allow_absolute_urls=False)",
                    **_error_context(current),
                )

            method = _redirect_method(current, response.status)
            method_changed = method != current.method
            headers = _rewrite_headers(
                current.headers,
                origin_changed=origin_changed,
                strip_auth=config.strip_auth_on_origin_change,
                method_changed=method_changed,
            )
            content = None if method_changed else current.content
            await response.aclose()
            current = Request(
                method=method,
                url=target,
                headers=headers,
                content=content,
                extensions=current.extensions,
            )
            hops += 1


__all__ = ("RedirectMiddleware",)
