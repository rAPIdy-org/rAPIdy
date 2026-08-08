from __future__ import annotations

import asyncio
import socket
import ssl
import time
from collections.abc import (
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    Mapping,
    Sequence,
)
from dataclasses import dataclass
from importlib import metadata
from typing import TYPE_CHECKING, Final, Literal, TypedDict, cast

import httpcore2
import httpx2

from rapidy_client._content import (
    ContentFactory,
    build_accept_encoding,
    decode_stream,
)
from rapidy_client._models import (
    BaseTransport,
    Headers,
    Request,
    Response,
    ResponseExtensions,
    Timeout,
)
from rapidy_client.errors import (
    ConnectError,
    DecodeError,
    DNSResolveError,
    HttpClientError,
    HttpTimeoutError,
    ProtocolError,
    ProxyError,
    ServerDisconnectedError,
    TLSError,
    TransportError,
)

if TYPE_CHECKING:
    from rapidy_client.config import PoolLimits, ProxyConfig, TLSConfig

_DEFAULT_SERVICE: Final = "rapidy-client"
_SERVER_DISCONNECTED = "server disconnected without"

# httpcore2 trace coverage and the semaphore-timing fallback are documented in
# docs/adr/0002-httpcore2-trace-spike.md.


class _ErrorContext(TypedDict):
    upstream: str | None
    endpoint: str | None
    request_id: str | None


@dataclass(slots=True)
class _TraceState:
    connection_reused: bool | None = None
    pool_wait: float | None = None

    async def __call__(self, name: str, info: dict[str, object]) -> None:
        del info
        if name == "connection.connect_tcp.started":
            self.connection_reused = False
        elif (
            name.endswith(".send_request_headers.started")
            and self.connection_reused is None
        ):
            self.connection_reused = True


def _default_user_agent() -> str:
    try:
        version = metadata.version("rapidy-client")
    except metadata.PackageNotFoundError:
        version = "0.0.0"
    return f"{_DEFAULT_SERVICE}/{version}"


def _h2_available() -> bool:
    try:
        import h2  # noqa: F401
    except ImportError:
        return False
    return True


def _ctx(request: Request) -> _ErrorContext:
    return {
        "upstream": request.extensions.upstream,
        "endpoint": request.extensions.endpoint,
        "request_id": request.extensions.request_id,
    }


def _cause_chain(exc: BaseException) -> list[BaseException]:
    result: list[BaseException] = []
    pending = [exc]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        result.append(current)
        if current.__cause__ is not None:
            pending.append(current.__cause__)
        if current.__context__ is not None:
            pending.append(current.__context__)
    return result


def _is_server_disconnected(exc: BaseException) -> bool:
    chain = _cause_chain(exc)
    has_core_reason = any(
        isinstance(item, httpcore2.RemoteProtocolError) for item in chain
    )
    has_message = any(_SERVER_DISCONNECTED in str(item).casefold() for item in chain)
    return has_core_reason and has_message


def _with_cause(
    mapped: HttpClientError | ValueError,
    cause: BaseException,
) -> HttpClientError | ValueError:
    mapped.__cause__ = cause
    return mapped


def map_transport_exception(
    exc: BaseException,
    *,
    request: Request | None = None,
) -> HttpClientError | ValueError:
    ctx: _ErrorContext = (
        _ctx(request)
        if request is not None
        else {"upstream": None, "endpoint": None, "request_id": None}
    )
    message = str(exc)

    if isinstance(exc, TimeoutError) and not isinstance(exc, httpx2.TimeoutException):
        mapped: HttpClientError | ValueError = HttpTimeoutError(
            message, phase="total", **ctx
        )
    elif isinstance(exc, httpx2.ConnectTimeout):
        mapped = HttpTimeoutError(message, phase="connect", **ctx)
    elif isinstance(exc, httpx2.ReadTimeout):
        mapped = HttpTimeoutError(message, phase="read", **ctx)
    elif isinstance(exc, httpx2.WriteTimeout):
        mapped = HttpTimeoutError(message, phase="write", **ctx)
    elif isinstance(exc, httpx2.PoolTimeout):
        mapped = HttpTimeoutError(message, phase="pool", **ctx)
    elif isinstance(exc, httpx2.ProxyError):
        mapped = ProxyError(message, **ctx)
    elif isinstance(exc, httpx2.ConnectError):
        causes = _cause_chain(exc)
        if any(isinstance(cause, ssl.SSLError) for cause in causes):
            mapped = TLSError(message, **ctx)
        elif any(isinstance(cause, socket.gaierror) for cause in causes):
            mapped = DNSResolveError(message, **ctx)
        else:
            mapped = ConnectError(message, **ctx)
    elif isinstance(exc, httpx2.RemoteProtocolError):
        mapped = (
            ServerDisconnectedError(message, **ctx)
            if _is_server_disconnected(exc)
            else ProtocolError(message, **ctx)
        )
    elif isinstance(exc, (httpx2.ReadError, httpx2.WriteError)):
        mapped = TransportError(message, **ctx)
    elif isinstance(exc, httpx2.DecodingError):
        mapped = DecodeError(message, **ctx)
    elif isinstance(exc, (httpx2.InvalidURL, httpx2.UnsupportedProtocol)):
        mapped = ValueError(message)
    else:
        mapped = TransportError(message, **ctx)
    return _with_cause(mapped, exc)


def _map_send_exception(
    exc: BaseException,
    *,
    request: Request,
    trace_state: _TraceState | None,
) -> HttpClientError | ValueError:
    """Map errors raised before response headers are received."""
    # httpcore2 2.9 reports a TCP reset between keep-alive requests as
    # ReadError; earlier releases reported RemoteProtocolError. The stable
    # public meaning is a server disconnect before the next response.
    if (
        trace_state is not None
        and trace_state.connection_reused is True
        and isinstance(exc, httpx2.ReadError)
    ):
        return _with_cause(
            ServerDisconnectedError(str(exc), **_ctx(request)),
            exc,
        )

    return map_transport_exception(exc, request=request)


class HttpxTransport(BaseTransport):
    def __init__(
        self,
        *,
        base_url: str,
        limits: PoolLimits,
        tls: TLSConfig,
        proxy: ProxyConfig | None = None,
        cookies: Literal["disabled", "shared"] = "disabled",
        default_headers: Mapping[str, str] = cast("Mapping[str, str]", ()),
        observers: Sequence[object] = (),
    ) -> None:
        if cookies not in {"disabled", "shared"}:
            raise ValueError("cookies must be 'disabled' or 'shared'")
        self._base_url = base_url
        self._limits = limits
        self._tls = tls
        self._proxy = proxy
        self._cookies = cookies
        self._observers = tuple(observers)
        self._default_headers = dict(default_headers)
        if not any(name.casefold() == "user-agent" for name in self._default_headers):
            self._default_headers["User-Agent"] = _default_user_agent()
        if not any(
            name.casefold() == "accept-encoding" for name in self._default_headers
        ):
            self._default_headers["Accept-Encoding"] = build_accept_encoding()
        self._client: httpx2.AsyncClient | None = None
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        self._closed = False

    def _build_limits(self) -> httpx2.Limits:
        return httpx2.Limits(
            max_connections=self._limits.max_connections,
            max_keepalive_connections=(
                0 if self._limits.force_close else self._limits.max_connections
            ),
            keepalive_expiry=self._limits.keepalive_timeout,
        )

    def _build_cookies(self) -> httpx2.Cookies | None:
        return httpx2.Cookies() if self._cookies == "shared" else None

    def _build_ssl(self) -> bool | ssl.SSLContext:
        if not self._tls.verify:
            return False
        context = ssl.create_default_context(
            cafile=str(self._tls.ca_file) if self._tls.ca_file else None
        )
        context.minimum_version = (
            ssl.TLSVersion.TLSv1_3
            if self._tls.min_version == "TLSv1_3"
            else ssl.TLSVersion.TLSv1_2
        )
        return context

    def _build_cert(self) -> tuple[str, str] | str | None:
        if self._tls.client_cert is None:
            return None
        if self._tls.client_key is None:
            return str(self._tls.client_cert)
        return str(self._tls.client_cert), str(self._tls.client_key)

    def _build_proxy(self) -> str | None:
        if self._proxy is None or self._proxy.url is None:
            return None
        return str(self._proxy.url)

    async def _get_client(self) -> httpx2.AsyncClient:
        if self._client is None:
            self._client = httpx2.AsyncClient(
                base_url=self._base_url,
                follow_redirects=False,
                http2=True if _h2_available() else False,  # noqa: SIM210
                timeout=httpx2.Timeout(None),
                limits=self._build_limits(),
                headers=self._default_headers,
                cookies=self._build_cookies(),
                verify=self._build_ssl(),
                cert=self._build_cert(),
                proxy=self._build_proxy(),
                trust_env=(self._proxy.trust_env if self._proxy is not None else False),
            )
        return self._client

    def _sem_for(self, host: str) -> asyncio.Semaphore:
        semaphore = self._semaphores.get(host)
        if semaphore is None:
            semaphore = asyncio.Semaphore(self._limits.max_per_host)
            self._semaphores[host] = semaphore
        return semaphore

    def _build_request(
        self,
        client: httpx2.AsyncClient,
        request: Request,
        timeout: Timeout,
    ) -> tuple[httpx2.Request, _TraceState]:
        content: bytes | AsyncIterable[bytes] | None
        if isinstance(request.content, ContentFactory):
            content = request.content.open()
        else:
            content = request.content
        trace_state = _TraceState()
        native_timeout = httpx2.Timeout(
            connect=timeout.connect,
            read=timeout.read,
            write=timeout.write,
            pool=timeout.pool,
        )
        native_request = client.build_request(
            request.method,
            request.url._raw_str(),
            headers=request.headers.multi_items(),
            content=content,
            timeout=native_timeout,
            extensions={"trace": trace_state},
        )
        return native_request, trace_state

    def _wrap_close(
        self,
        native_response: httpx2.Response,
        semaphore: asyncio.Semaphore,
        request: Request,
    ) -> Callable[[], Awaitable[None]]:
        closed = False

        async def close() -> None:
            nonlocal closed
            if closed:
                return
            closed = True
            try:
                await native_response.aclose()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                raise map_transport_exception(exc, request=request) from exc
            finally:
                semaphore.release()

        return close

    async def _wrap_stream(
        self,
        native_response: httpx2.Response,
        request: Request,
        close: Callable[[], Awaitable[None]],
    ) -> AsyncIterator[bytes]:
        try:
            if hasattr(native_response, "_content"):
                yield native_response.content
            else:
                async for chunk in native_response.aiter_raw():
                    yield chunk
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            raise map_transport_exception(exc, request=request) from exc
        finally:
            await close()

    async def _decode_response_stream(
        self,
        encodings: list[str],
        source: AsyncIterable[bytes],
        close: Callable[[], Awaitable[None]],
    ) -> AsyncIterator[bytes]:
        try:
            async for chunk in decode_stream(encodings, source):
                yield chunk
        finally:
            # decode_stream may reject an encoding before it starts consuming
            # source, so its inner transport stream cannot release the slot.
            await close()

    def _build_response(
        self,
        request: Request,
        native_response: httpx2.Response,
        extensions: ResponseExtensions,
        semaphore: asyncio.Semaphore,
    ) -> Response:
        close = self._wrap_close(native_response, semaphore, request)
        content_encoding = native_response.headers.get("content-encoding", "")
        encodings = [
            token
            for value in content_encoding.split(",")
            if (token := value.strip().casefold()) and token != "identity"
        ]
        raw_stream = self._wrap_stream(native_response, request, close)
        # A pre-buffered native response has already passed through httpx2's
        # decoder. Real stream=True responses remain raw and are decoded here.
        stream = (
            raw_stream
            if hasattr(native_response, "_content") or not encodings
            else self._decode_response_stream(encodings, raw_stream, close)
        )
        return Response(
            status=native_response.status_code,
            headers=Headers(native_response.headers.multi_items()),
            request=request,
            extensions=extensions,
            stream=stream,
            on_close=close,
        )

    async def handle(self, request: Request) -> Response:
        if self._closed:
            raise RuntimeError("HttpxTransport is closed")
        client = await self._get_client()
        timeout = request.extensions.timeout
        semaphore = self._sem_for(request.url.host or "")
        pool_wait_started = time.monotonic()
        try:
            async with asyncio.timeout(timeout.pool):
                await semaphore.acquire()
        except TimeoutError:
            raise HttpTimeoutError(phase="pool", **_ctx(request)) from None

        semaphore_wait = time.monotonic() - pool_wait_started
        acquired = True
        native_response: httpx2.Response | None = None
        trace_state: _TraceState | None = None
        try:
            try:
                native_request, trace_state = self._build_request(
                    client, request, timeout
                )
                started = time.monotonic()
                native_response = await client.send(native_request, stream=True)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                raise _map_send_exception(
                    exc,
                    request=request,
                    trace_state=trace_state,
                ) from exc

            if self._cookies == "disabled":
                client.cookies.clear()
            assert not hasattr(native_response, "_status_raised"), (
                "status exceptions must never be raised by the transport"
            )
            response_extensions = ResponseExtensions(
                elapsed=time.monotonic() - started,
                attempt=request.extensions.attempt,
                connection_reused=trace_state.connection_reused,
                pool_wait=(
                    trace_state.pool_wait
                    if trace_state.pool_wait is not None
                    else semaphore_wait
                ),
            )
            response = self._build_response(
                request,
                native_response,
                response_extensions,
                semaphore,
            )
            acquired = False
            return response
        finally:
            if acquired:
                semaphore.release()
                if native_response is not None:
                    await native_response.aclose()

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._client is not None:
            await self._client.aclose()


__all__ = ("HttpxTransport", "map_transport_exception")
