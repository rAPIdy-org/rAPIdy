import asyncio
import gzip
import ssl
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import httpx2
import pytest
import rapidy_client.transports.httpx as transport_module
from rapidy_client import (
    UNSET,
    URL,
    ContentFactory,
    DecodeError,
    Headers,
    HttpTimeoutError,
    ProtocolError,
    Request,
    RequestExtensions,
    ResponseExtensions,
    ServerDisconnectedError,
    Timeout,
)
from rapidy_client.transports import BaseTransport, HttpxTransport


@dataclass(slots=True)
class PoolLimits:
    max_connections: int = 10
    max_per_host: int = 2
    keepalive_timeout: float = 15.0
    force_close: bool = False


@dataclass(slots=True)
class TLSConfig:
    verify: bool = True
    ca_file: Path | None = None
    min_version: str = "TLSv1_2"
    client_cert: Path | None = None
    client_key: Path | None = None


@dataclass(slots=True)
class ProxyConfig:
    url: str | None = None
    trust_env: bool = False


def _transport(
    *,
    limits: PoolLimits | None = None,
    tls: TLSConfig | None = None,
    cookies: str = "disabled",
    default_headers: dict[str, str] | None = None,
) -> HttpxTransport:
    return HttpxTransport(
        base_url="https://example.test",
        limits=limits or PoolLimits(),  # type: ignore[arg-type]
        tls=tls or TLSConfig(),  # type: ignore[arg-type]
        cookies=cast(Any, cookies),
        default_headers=default_headers or {},
    )


def _request(
    *,
    content: Any = None,
    timeout: Timeout | None = None,
    url: str = "https://example.test/path?token=SECRET",
    attempt: int = 0,
) -> Request:
    extensions = RequestExtensions(
        upstream="test",
        endpoint="/path",
        request_id="request-1",
        timeout=timeout or Timeout(),
        retry=None,
        idempotent=True,
        auth_override=UNSET,
        deadline=None,
        redirects=None,  # type: ignore[arg-type]
        attempt=attempt,
    )
    return Request(
        method="POST" if content is not None else "GET",
        url=URL(url),
        headers=Headers({"X-Request": "yes"}),
        content=content,
        extensions=extensions,
    )


def _install_mock_client(
    monkeypatch: pytest.MonkeyPatch,
    handler: Callable[[httpx2.Request], Awaitable[httpx2.Response]],
) -> dict[str, Any]:
    native_client = httpx2.AsyncClient
    captured: dict[str, Any] = {}

    def factory(**kwargs: Any) -> httpx2.AsyncClient:
        captured.update(kwargs)
        return native_client(
            **kwargs,
            transport=httpx2.MockTransport(handler),
        )

    monkeypatch.setattr(transport_module.httpx2, "AsyncClient", factory)
    return captured


async def _perform(transport: HttpxTransport, request: Request) -> bytes:
    response = await transport.handle(request)
    return await response.aread()


def test_public_import_surface() -> None:
    assert issubclass(HttpxTransport, BaseTransport)


def test_reused_connection_reset_maps_server_disconnected() -> None:
    trace_state = transport_module._TraceState()
    trace_state.connection_reused = True
    source = httpx2.ReadError("connection reset")

    result = transport_module._map_send_exception(
        source,
        request=_request(),
        trace_state=trace_state,
    )

    assert isinstance(result, ServerDisconnectedError)
    assert result.__cause__ is source


@pytest.mark.asyncio
async def test_maps_timeout_phases_to_httpx2_timeout() -> None:
    transport = _transport()
    client = await transport._get_client()
    timeout = Timeout(connect=3.0, read=10.0, write=30.0, pool=5.0)
    native_request, _ = transport._build_request(
        client, _request(timeout=timeout), timeout
    )
    assert native_request.extensions["timeout"] == {
        "connect": 3.0,
        "read": 10.0,
        "write": 30.0,
        "pool": 5.0,
    }
    await transport.aclose()


@pytest.mark.asyncio
async def test_follow_redirects_false(monkeypatch: pytest.MonkeyPatch) -> None:
    async def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200)

    captured = _install_mock_client(monkeypatch, handler)
    transport = _transport()
    await transport._get_client()
    assert captured["follow_redirects"] is False
    await transport.aclose()


def test_default_user_agent_set() -> None:
    user_agent = _transport()._default_headers["User-Agent"]
    service, separator, version = user_agent.partition("/")
    assert (service, separator) == ("rapidy-client", "/")
    assert version


def test_default_user_agent_not_overridden() -> None:
    transport = _transport(default_headers={"user-agent": "svc/1.2"})
    assert transport._default_headers["user-agent"] == "svc/1.2"


def test_default_accept_encoding_set() -> None:
    transport = _transport()
    assert transport._default_headers["Accept-Encoding"].startswith("gzip")
    assert "deflate" not in transport._default_headers["Accept-Encoding"]


def test_default_accept_encoding_not_overridden_case_insensitively() -> None:
    transport = _transport(default_headers={"accept-encoding": "identity"})
    assert transport._default_headers["accept-encoding"] == "identity"
    assert "Accept-Encoding" not in transport._default_headers


def test_default_headers_applied() -> None:
    transport = _transport(default_headers={"X-Env": "prod"})
    assert transport._default_headers["X-Env"] == "prod"


@pytest.mark.asyncio
@pytest.mark.parametrize(("available", "expected"), [(True, True), (False, False)])
async def test_http2_follows_h2_availability(
    monkeypatch: pytest.MonkeyPatch,
    available: bool,
    expected: bool,
) -> None:
    async def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200)

    captured = _install_mock_client(monkeypatch, handler)
    monkeypatch.setattr(transport_module, "_h2_available", lambda: available)
    transport = _transport()
    await transport._get_client()
    assert captured["http2"] is expected
    await transport.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("policy", "expected_second_cookie"),
    [("disabled", None), ("shared", "sid=one")],
)
async def test_cookie_policy(
    monkeypatch: pytest.MonkeyPatch,
    policy: str,
    expected_second_cookie: str | None,
) -> None:
    seen: list[str | None] = []

    async def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request.headers.get("cookie"))
        return httpx2.Response(
            200,
            headers={"Set-Cookie": "sid=one; Path=/"},
            content=b"ok",
        )

    _install_mock_client(monkeypatch, handler)
    transport = _transport(cookies=policy)
    assert await _perform(transport, _request()) == b"ok"
    assert await _perform(transport, _request()) == b"ok"
    assert seen == [None, expected_second_cookie]
    await transport.aclose()


def test_tls_min_version_context() -> None:
    context = _transport(tls=TLSConfig(min_version="TLSv1_3"))._build_ssl()
    assert isinstance(context, ssl.SSLContext)
    assert context.minimum_version == ssl.TLSVersion.TLSv1_3


def test_tls_verify_false() -> None:
    assert _transport(tls=TLSConfig(verify=False))._build_ssl() is False


def test_tls_client_cert_mtls() -> None:
    transport = _transport(
        tls=TLSConfig(
            client_cert=Path("/cert.pem"),
            client_key=Path("/key.pem"),
        )
    )
    assert transport._build_cert() == ("/cert.pem", "/key.pem")


def test_limits_force_close() -> None:
    limits = _transport(limits=PoolLimits(force_close=True))._build_limits()
    assert limits.max_keepalive_connections == 0


def test_limits_keepalive_expiry() -> None:
    limits = _transport(limits=PoolLimits(keepalive_timeout=15.0))._build_limits()
    assert limits.keepalive_expiry == 15.0


@pytest.mark.asyncio
async def test_semaphore_serializes_per_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active = 0
    max_active = 0

    async def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal active, max_active
        active += 1
        max_active = max(active, max_active)
        await asyncio.sleep(0.03)
        active -= 1
        return httpx2.Response(200, content=b"ok")

    _install_mock_client(monkeypatch, handler)
    transport = _transport(limits=PoolLimits(max_per_host=1))
    await asyncio.gather(
        _perform(transport, _request()),
        _perform(transport, _request()),
    )
    assert max_active == 1
    await transport.aclose()


@pytest.mark.asyncio
async def test_semaphore_timeout_maps_pool_phase(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, content=b"held")

    _install_mock_client(monkeypatch, handler)
    transport = _transport(limits=PoolLimits(max_per_host=1))
    first = await transport.handle(_request())
    with pytest.raises(HttpTimeoutError) as error:
        await transport.handle(_request(timeout=Timeout(pool=0.01)))
    assert error.value.phase == "pool"
    await first.aclose()
    await transport.aclose()


@pytest.mark.asyncio
async def test_no_raise_for_status(monkeypatch: pytest.MonkeyPatch) -> None:
    async def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(503, content=b"unavailable")

    _install_mock_client(monkeypatch, handler)
    transport = _transport()
    response = await transport.handle(_request())
    assert response.status == 503
    await response.aread()
    await transport.aclose()


@pytest.mark.asyncio
async def test_response_extensions_populated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, content=b"ok")

    _install_mock_client(monkeypatch, handler)
    transport = _transport()
    response = await transport.handle(_request(attempt=3))
    assert response.extensions.elapsed >= 0
    assert response.extensions.attempt == 3
    assert response.extensions.connection_reused is None
    assert response.extensions.pool_wait is not None
    await response.aread()
    await transport.aclose()


@pytest.mark.asyncio
async def test_content_factory_reopened_per_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened = 0
    received: list[bytes] = []

    def factory() -> bytes:
        nonlocal opened
        opened += 1
        return b"body"

    async def handler(request: httpx2.Request) -> httpx2.Response:
        received.append(await request.aread())
        return httpx2.Response(200, content=b"ok")

    _install_mock_client(monkeypatch, handler)
    transport = _transport()
    request = _request(content=ContentFactory(factory))
    await _perform(transport, request)
    await _perform(transport, request)
    assert opened == 2
    assert received == [b"body", b"body"]
    await transport.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("content", [b"body", None])
async def test_content_passed(
    monkeypatch: pytest.MonkeyPatch,
    content: bytes | None,
) -> None:
    received: list[bytes] = []

    async def handler(request: httpx2.Request) -> httpx2.Response:
        received.append(await request.aread())
        return httpx2.Response(200, content=b"ok")

    _install_mock_client(monkeypatch, handler)
    transport = _transport()
    await _perform(transport, _request(content=content))
    assert received == [content or b""]
    await transport.aclose()


@pytest.mark.asyncio
async def test_default_accept_encoding_applied_to_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[str] = []

    async def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request.headers["accept-encoding"])
        return httpx2.Response(200, content=b"ok")

    _install_mock_client(monkeypatch, handler)
    transport = _transport()
    await _perform(transport, _request())
    assert seen == [transport._default_headers["Accept-Encoding"]]
    await transport.aclose()


@pytest.mark.asyncio
async def test_transport_decodes_content_encoding_incrementally(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    encoded = gzip.compress(b"decoded body" * 20)

    class RawStream(httpx2.AsyncByteStream):
        async def __aiter__(self) -> AsyncIterator[bytes]:
            for index in range(0, len(encoded), 3):
                yield encoded[index : index + 3]

    async def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200,
            headers={"Content-Encoding": "gzip"},
            stream=RawStream(),
        )

    _install_mock_client(monkeypatch, handler)
    transport = _transport()
    assert await _perform(transport, _request()) == b"decoded body" * 20
    await transport.aclose()


@pytest.mark.asyncio
async def test_transport_unknown_content_encoding_raises_decode_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class RawStream(httpx2.AsyncByteStream):
        async def __aiter__(self) -> AsyncIterator[bytes]:
            yield b"encoded"

    async def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200,
            headers={"Content-Encoding": "made-up"},
            stream=RawStream(),
        )

    _install_mock_client(monkeypatch, handler)
    transport = _transport()
    response = await transport.handle(_request())
    with pytest.raises(DecodeError, match="made-up"):
        await response.aread()
    assert transport._sem_for("example.test").locked() is False
    await transport.aclose()


@pytest.mark.asyncio
async def test_stream_wrapper_maps_body_errors() -> None:
    class BrokenStream(httpx2.AsyncByteStream):
        async def __aiter__(self) -> AsyncIterator[bytes]:
            yield b"partial"
            raise httpx2.RemoteProtocolError("malformed body")

    transport = _transport()
    native_response = httpx2.Response(
        200,
        request=httpx2.Request("GET", "https://example.test"),
        stream=BrokenStream(),
    )
    semaphore = asyncio.Semaphore(1)
    await semaphore.acquire()
    response = transport._build_response(
        _request(),
        native_response,
        ResponseExtensions(elapsed=0, attempt=0),
        semaphore,
    )
    with pytest.raises(ProtocolError):
        await response.aread()
    assert not semaphore.locked()


@pytest.mark.asyncio
async def test_aclose_idempotent() -> None:
    class Client:
        closes = 0

        async def aclose(self) -> None:
            self.closes += 1

    transport = _transport()
    client = Client()
    transport._client = cast(Any, client)
    await transport.aclose()
    await transport.aclose()
    assert client.closes == 1


def test_no_client_created_without_handle() -> None:
    assert _transport()._client is None
