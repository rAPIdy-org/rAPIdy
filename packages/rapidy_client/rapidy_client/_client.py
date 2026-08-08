from __future__ import annotations

import asyncio
import dataclasses
import logging
import warnings
from collections.abc import AsyncIterable, Mapping, Sequence
from contextlib import AbstractAsyncContextManager
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Protocol
from urllib.parse import quote, urlencode
from uuid import UUID

from pydantic import BaseModel
from rapidy_core import UNSET, Unset
from rapidy_core.encoders import jsonify

from rapidy_client._clock import Clock, SystemClock
from rapidy_client._content import ContentFactory, FilePart
from rapidy_client._models import (
    URL,
    AuthPolicy,
    BaseTransport,
    CallNext,
    Headers,
    Middleware,
    QueryValue,
    Request,
    RequestExtensions,
    Response,
    Timeout,
)
from rapidy_client._pipeline import build_pipeline
from rapidy_client.config import (
    RetryConfig,
    UpstreamConfig,
    client_debug_enabled,
    rapidy_client_deadline,
    rapidy_client_request_id,
    render_effective_config,
)
from rapidy_client.errors import ClientClosedError, StatusError
from rapidy_client.middleware.redirect import RedirectMiddleware
from rapidy_client.transports.httpx import HttpxTransport

_IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "PUT", "DELETE", "OPTIONS", "TRACE"})
_JSON_CONTENT_TYPE = "application/json"
_FORM_CONTENT_TYPE = "application/x-www-form-urlencoded"
_LOGGER = logging.getLogger(__name__)


class _Drainable(Protocol):
    async def aclose(self) -> None: ...


class _FiniteDrainable(_Drainable, Protocol):
    async def wait_closed(self) -> None: ...


def _apply_timeout_level(
    base: Timeout,
    level: Timeout | float | None | Unset,
) -> Timeout:
    if level is UNSET:
        return base
    if level is None:
        return dataclasses.replace(base, total=None)
    if isinstance(level, Timeout):
        return level
    if not isinstance(level, (int, float)):
        raise TypeError("timeout override must be Timeout, float, None, or UNSET")
    return dataclasses.replace(base, total=float(level))


def _merge_timeout(
    levels: Sequence[Timeout | float | None | Unset],
    *,
    base: Timeout,
) -> Timeout:
    effective = base
    for level in levels:
        effective = _apply_timeout_level(effective, level)
    return effective


def _query_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, bool):
        return ["true" if value else "false"]
    if isinstance(value, datetime):
        normalized = (
            value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        )
        return [normalized.isoformat()]
    if isinstance(value, date):
        return [value.isoformat()]
    if isinstance(value, Enum):
        return [str(value.value)]
    if isinstance(value, UUID):
        return [str(value)]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [item for part in value for item in _query_values(part)]
    return [str(value)]


def _serialize_query(
    query: Mapping[str, QueryValue] | BaseModel | None,
) -> list[tuple[str, str]]:
    if query is None:
        return []
    values: Mapping[str, Any]
    if isinstance(query, BaseModel):
        values = query.model_dump(mode="json", by_alias=True, exclude_none=True)
    else:
        values = query
    return [
        (str(name), item)
        for name, value in values.items()
        for item in _query_values(value)
    ]


def _serialize_headers(
    headers: Mapping[str, str] | BaseModel | None,
) -> Headers:
    if headers is None:
        return Headers()
    if isinstance(headers, BaseModel):
        values = headers.model_dump(mode="json", by_alias=True, exclude_none=True)
        return Headers((str(name), str(value)) for name, value in values.items())
    return Headers(headers)


def _with_content_type(headers: Headers, content_type: str) -> Headers:
    if "content-type" in headers:
        return headers
    return Headers((*headers.multi_items(), ("Content-Type", content_type)))


class HttpClient:
    def __init__(
        self,
        config: UpstreamConfig,
        *,
        name: str = "default",
        transport: BaseTransport | None = None,
        middlewares: Sequence[Middleware] = (),
        per_attempt_middlewares: Sequence[Middleware] = (),
        auth: AuthPolicy | None = None,
        observers: Sequence[object] = (),
        _clock: Clock | None = None,
    ) -> None:
        self._config = config
        self._name = name
        self._owns_transport = transport is None
        self._transport: BaseTransport = (
            transport
            if transport is not None
            else HttpxTransport(
                base_url=str(config.base_url),
                limits=config.limits,
                tls=config.tls,
                proxy=config.proxy,
                cookies=config.cookies,
                default_headers=config.default_headers,
                observers=observers,
            )
        )
        self._auth = auth
        self._middlewares = tuple(middlewares)
        self._observers = tuple(observers)
        self._clock = _clock if _clock is not None else SystemClock()
        self._entry: CallNext = build_pipeline(
            self._transport,
            middlewares=self._middlewares,
            per_attempt_middlewares=per_attempt_middlewares,
            redirect=RedirectMiddleware(
                allow_absolute_urls=self._config.allow_absolute_urls,
                max_response_size=self._config.max_response_size,
            ),
            debug=client_debug_enabled(),
        )
        self._loop: asyncio.AbstractEventLoop | None = None
        self._closing = False
        self._closed = False
        self._inflight: set[asyncio.Task[Response]] = set()
        self._finite: set[_FiniteDrainable] = set()
        self._infinite: set[_Drainable] = set()

    @classmethod
    def simple(
        cls,
        base_url: str,
        **overrides: Any,
    ) -> AbstractAsyncContextManager[HttpClient]:
        return _SimpleCM(cls, base_url, overrides)

    def _bind_loop(self) -> None:
        running = asyncio.get_running_loop()
        if self._loop is None:
            self._loop = running
        elif self._loop is not running:
            raise RuntimeError("HttpClient is bound to another event loop")

    def _effective_timeout(
        self,
        timeout: Timeout | float | None | Unset,
        *,
        stream: bool,
    ) -> Timeout:
        if stream and timeout is UNSET:
            return dataclasses.replace(self._config.timeout, total=None)
        return _merge_timeout((UNSET, timeout), base=self._config.timeout)

    def _effective_deadline(self, deadline: float | Unset) -> float | None:
        if deadline is not UNSET:
            return self._clock.monotonic() + float(deadline)
        if self._config.deadline.respect_incoming:
            incoming = rapidy_client_deadline.get()
            if incoming is not None:
                return self._clock.monotonic() + incoming
        return None

    def _build_url(
        self,
        path: str,
        *,
        path_params: Mapping[str, object] | None,
        query: Mapping[str, QueryValue] | BaseModel | None,
    ) -> URL:
        if "://" in path and not self._config.allow_absolute_urls:
            raise ValueError("absolute URLs are disabled for this upstream")
        rendered_path = path
        for name, value in (path_params or {}).items():
            rendered_path = rendered_path.replace(
                "{" + name + "}",
                quote(str(value), safe=""),
            )
        url = URL(str(self._config.base_url)).join(rendered_path)
        pairs = _serialize_query(query)
        if pairs:
            raw = url._raw_str()
            url = URL(raw + ("&" if "?" in raw else "?") + urlencode(pairs))
        return url

    def _build_body(
        self,
        *,
        headers: Headers,
        json: Any,
        content: bytes | AsyncIterable[bytes] | ContentFactory | None,
        data: Mapping[str, str] | None,
        files: Sequence[FilePart] | None,
    ) -> tuple[
        bytes | AsyncIterable[bytes] | ContentFactory | None,
        Headers,
    ]:
        sources = sum(value is not None for value in (json, content, data, files))
        if sources > 1:
            raise ValueError("multiple request body sources were provided")
        if json is not None:
            encoded = jsonify(json, dumps=True).encode("utf-8")
            return encoded, _with_content_type(headers, _JSON_CONTENT_TYPE)
        if content is not None:
            return content, headers
        if data is not None:
            encoded = urlencode(sorted(data.items())).encode("utf-8")
            return encoded, _with_content_type(headers, _FORM_CONTENT_TYPE)
        if files is not None:
            raise NotImplementedError("multipart/files are implemented in milestone 18")
        return None, headers

    def _build_request(
        self,
        method: str,
        path: str,
        *,
        path_params: Mapping[str, object] | None = None,
        query: Mapping[str, QueryValue] | BaseModel | None = None,
        headers: Mapping[str, str] | BaseModel | None = None,
        json: Any = None,
        content: bytes | AsyncIterable[bytes] | ContentFactory | None = None,
        data: Mapping[str, str] | None = None,
        files: Sequence[FilePart] | None = None,
        timeout: Timeout | float | None | Unset = UNSET,
        retry: RetryConfig | None | Unset = UNSET,
        auth: AuthPolicy | None | Unset = UNSET,
        follow_redirects: bool | Unset = UNSET,
        deadline: float | Unset = UNSET,
        stream: bool = False,
    ) -> Request:
        effective_timeout = self._effective_timeout(timeout, stream=stream)
        effective_retry = self._config.retry if retry is UNSET else retry
        effective_redirects = (
            self._config.redirects
            if follow_redirects is UNSET
            else self._config.redirects.model_copy(update={"follow": follow_redirects})
        )
        effective_deadline = self._effective_deadline(deadline)
        headers_obj = _serialize_headers(headers)
        body, headers_obj = self._build_body(
            headers=headers_obj,
            json=json,
            content=content,
            data=data,
            files=files,
        )
        upper_method = method.upper()
        request = Request(
            method=upper_method,
            url=self._build_url(path, path_params=path_params, query=query),
            headers=headers_obj,
            content=body,
            extensions=RequestExtensions(
                upstream=self._name,
                endpoint=path,
                request_id=rapidy_client_request_id.get(),
                timeout=effective_timeout,
                retry=effective_retry,
                idempotent=upper_method in _IDEMPOTENT_METHODS,
                auth_override=auth,
                deadline=effective_deadline,
                redirects=effective_redirects,
            ),
        )
        if client_debug_enabled():
            _LOGGER.debug(
                "%s",
                render_effective_config(
                    upstream_name=self._name,
                    endpoint=path,
                    timeout=effective_timeout,
                    retry=effective_retry,
                    redirects=effective_redirects,
                    deadline=effective_deadline,
                ),
            )
        return request

    async def _execute_buffered(
        self,
        request: Request,
        *,
        raise_for_status: bool,
    ) -> Response:
        response = await self._entry(request)
        is_error = response.is_client_error or response.is_server_error
        if raise_for_status:
            if is_error:
                await response._aread_capped(self._config.error_body_limit)
            else:
                await response.aread()
        if raise_for_status and is_error:
            raise StatusError(
                f"HTTP response status {response.status}",
                status=response.status,
                response=response,
                error_model=None,
            )
        return response

    async def request(
        self,
        method: str,
        path: str,
        *,
        path_params: Mapping[str, object] | None = None,
        query: Mapping[str, QueryValue] | BaseModel | None = None,
        headers: Mapping[str, str] | BaseModel | None = None,
        json: Any = None,
        content: bytes | AsyncIterable[bytes] | ContentFactory | None = None,
        data: Mapping[str, str] | None = None,
        files: Sequence[FilePart] | None = None,
        timeout: Timeout | float | None | Unset = UNSET,
        retry: RetryConfig | None | Unset = UNSET,
        auth: AuthPolicy | None | Unset = UNSET,
        follow_redirects: bool | Unset = UNSET,
        deadline: float | Unset = UNSET,
        raise_for_status: bool = True,
    ) -> Response:
        if self._closing:
            raise ClientClosedError("HttpClient is closed")
        self._bind_loop()
        built = self._build_request(
            method,
            path,
            path_params=path_params,
            query=query,
            headers=headers,
            json=json,
            content=content,
            data=data,
            files=files,
            timeout=timeout,
            retry=retry,
            auth=auth,
            follow_redirects=follow_redirects,
            deadline=deadline,
        )
        task = asyncio.ensure_future(
            self._execute_buffered(built, raise_for_status=raise_for_status)
        )
        self._inflight.add(task)
        try:
            return await task
        except asyncio.CancelledError:
            if self._closing:
                raise ClientClosedError(
                    "HttpClient closed while the request was in flight"
                ) from None
            raise
        finally:
            self._inflight.discard(task)

    async def get(self, path: str, **kwargs: Any) -> Response:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> Response:
        return await self.request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs: Any) -> Response:
        return await self.request("PUT", path, **kwargs)

    async def patch(self, path: str, **kwargs: Any) -> Response:
        return await self.request("PATCH", path, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> Response:
        return await self.request("DELETE", path, **kwargs)

    async def head(self, path: str, **kwargs: Any) -> Response:
        return await self.request("HEAD", path, **kwargs)

    async def options(self, path: str, **kwargs: Any) -> Response:
        return await self.request("OPTIONS", path, **kwargs)

    def stream(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> AbstractAsyncContextManager[Response]:
        return _StreamCM(self, method, path, kwargs)

    def ws(self, path: str, **kwargs: Any) -> Any:
        del path, kwargs
        if self._closing:
            raise ClientClosedError("HttpClient is closed")
        raise NotImplementedError("WebSocket sessions are implemented in milestone 19")

    def sse(self, path: str, **kwargs: Any) -> Any:
        del path, kwargs
        if self._closing:
            raise ClientClosedError("HttpClient is closed")
        raise NotImplementedError("SSE sessions are implemented in milestone 19")

    async def _safe_aclose(self, drainable: _Drainable) -> None:
        try:
            await drainable.aclose()
        except Exception:  # noqa: BLE001 - shutdown must continue through all resources
            return

    async def aclose(self, *, drain_timeout: float = 10.0) -> None:
        if self._closed:
            return
        self._closed = True
        self._closing = True

        infinite = tuple(self._infinite)
        self._infinite.clear()
        if infinite:
            await asyncio.gather(
                *(self._safe_aclose(item) for item in infinite),
                return_exceptions=True,
            )

        finite_waiters = {
            asyncio.create_task(item.wait_closed()) for item in tuple(self._finite)
        }
        pending: set[asyncio.Future[Any]] = set(self._inflight)
        pending.update(finite_waiters)
        if pending:
            await asyncio.wait(pending, timeout=drain_timeout)

        for waiter in finite_waiters:
            if not waiter.done():
                waiter.cancel()

        for task in tuple(self._inflight):
            if not task.done():
                task.cancel()
        for finite in tuple(self._finite):
            await self._safe_aclose(finite)

        if finite_waiters:
            await asyncio.gather(*finite_waiters, return_exceptions=True)

        tail = tuple(self._inflight)
        if tail:
            await asyncio.gather(*tail, return_exceptions=True)
        if self._owns_transport:
            await self._transport.aclose()


class _StreamCM(AbstractAsyncContextManager[Response]):
    def __init__(
        self,
        client: HttpClient,
        method: str,
        path: str,
        kwargs: dict[str, Any],
    ) -> None:
        self._client = client
        self._method = method
        self._path = path
        self._kwargs = dict(kwargs)
        self._task: asyncio.Task[Response] | None = None
        self._response: Response | None = None
        self._entered = False
        self._exited = False
        self._closed_event: asyncio.Event | None = None

    async def __aenter__(self) -> Response:
        if self._client._closing:
            raise ClientClosedError("HttpClient is closed")
        if self._entered:
            raise RuntimeError("stream context manager cannot be entered twice")
        self._entered = True
        self._closed_event = asyncio.Event()
        self._client._bind_loop()
        raise_for_status = bool(self._kwargs.pop("raise_for_status", True))
        request = self._client._build_request(
            self._method,
            self._path,
            stream=True,
            **self._kwargs,
        )
        self._task = asyncio.ensure_future(self._client._entry(request))
        self._client._inflight.add(self._task)
        self._client._finite.add(self)
        try:
            self._response = await self._task
            if raise_for_status and (
                self._response.is_client_error or self._response.is_server_error
            ):
                raise StatusError(
                    f"HTTP response status {self._response.status}",
                    status=self._response.status,
                    response=self._response,
                    error_model=None,
                )
            return self._response
        except BaseException:
            await self.aclose()
            raise

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> None:
        del exc_type, exc, tb
        await self.aclose()

    async def aclose(self) -> None:
        if self._exited:
            return
        self._exited = True
        try:
            self._client._finite.discard(self)
            task = self._task
            if task is not None:
                self._client._inflight.discard(task)
                if not task.done():
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
            if self._response is not None:
                await self._response.aclose()
        finally:
            if self._closed_event is not None:
                self._closed_event.set()

    async def wait_closed(self) -> None:
        if self._closed_event is not None:
            await self._closed_event.wait()

    def __del__(self) -> None:
        if self._entered and not self._exited and client_debug_enabled():
            warnings.warn("unclosed HttpClient stream", ResourceWarning, stacklevel=2)


class _SimpleCM(AbstractAsyncContextManager[HttpClient]):
    def __init__(
        self,
        client_type: type[HttpClient],
        base_url: str,
        overrides: dict[str, Any],
    ) -> None:
        self._client_type = client_type
        self._base_url = base_url
        self._overrides = dict(overrides)
        self._client: HttpClient | None = None
        self._entered = False

    async def __aenter__(self) -> HttpClient:
        if self._entered:
            raise RuntimeError("simple context manager cannot be entered twice")
        self._entered = True
        config = UpstreamConfig.model_validate(
            {"base_url": self._base_url, **self._overrides}
        )
        self._client = self._client_type(config)
        return self._client

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> None:
        del exc_type, exc, tb
        if self._client is not None:
            await self._client.aclose()

    def __del__(self) -> None:
        if not self._entered and client_debug_enabled():
            warnings.warn(
                "HttpClient.simple() was not used as a context manager",
                ResourceWarning,
                stacklevel=2,
            )


__all__ = ("HttpClient",)
