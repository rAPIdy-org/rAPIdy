from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import pytest
import rapidy_client._client as client_module
from rapidy_client import (
    UNSET,
    ClientClosedError,
    FilePart,
    Headers,
    HttpClient,
    RedirectConfig,
    Request,
    Response,
    ResponseExtensions,
    RetryConfig,
    StatusError,
    Timeout,
    UpstreamConfig,
)
from rapidy_client.config import rapidy_client_deadline, rapidy_client_request_id


async def _body_stream(body: bytes) -> AsyncIterator[bytes]:
    if body:
        yield body


class _RecordingTransport:
    def __init__(self, *, status: int = 200, body: bytes = b"") -> None:
        self.status = status
        self.body = body
        self.requests: list[Request] = []
        self.closes = 0

    @property
    def last(self) -> Request:
        return self.requests[-1]

    async def handle(self, request: Request) -> Response:
        self.requests.append(request)
        return Response(
            status=self.status,
            headers=Headers(),
            request=request,
            extensions=ResponseExtensions(elapsed=0.0, attempt=1),
            stream=_body_stream(self.body),
        )

    async def aclose(self) -> None:
        self.closes += 1


class _BlockingTransport(_RecordingTransport):
    def __init__(self, log: list[str] | None = None) -> None:
        super().__init__()
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.log = log if log is not None else []

    async def handle(self, request: Request) -> Response:
        self.requests.append(request)
        self.entered.set()
        try:
            await self.release.wait()
        except asyncio.CancelledError:
            self.log.append("cancel")
            raise
        self.log.append("complete")
        return Response(
            status=200,
            headers=Headers(),
            request=request,
            extensions=ResponseExtensions(elapsed=0.0, attempt=1),
        )

    async def aclose(self) -> None:
        self.log.append("close")
        await super().aclose()


class _FakeInfinite:
    def __init__(self) -> None:
        self.closed = asyncio.Event()

    async def aclose(self) -> None:
        self.closed.set()


class _FakeClock:
    def __init__(self, now: float = 100.0) -> None:
        self.now = now

    def monotonic(self) -> float:
        return self.now

    async def sleep(self, delay: float) -> None:
        self.now += delay


class _StatusSpy:
    def __init__(self) -> None:
        self.statuses: list[int] = []

    async def __call__(self, request: Request, call_next: Any) -> Response:
        response = await call_next(request)
        self.statuses.append(response.status)
        return response


class _AuthPolicy:
    pass


def _config(**overrides: Any) -> UpstreamConfig:
    return UpstreamConfig.model_validate(
        {"base_url": "https://api.example.com", **overrides}
    )


def _client(
    *,
    config: UpstreamConfig | None = None,
    transport: _RecordingTransport | None = None,
    **kwargs: Any,
) -> tuple[HttpClient, _RecordingTransport]:
    actual_transport = transport or _RecordingTransport()
    return (
        HttpClient(
            config or _config(),
            transport=actual_transport,
            **kwargs,
        ),
        actual_transport,
    )


@pytest.mark.asyncio
async def test_merge_timeout_call_overrides_total() -> None:
    config = _config(timeout=Timeout(total=10, connect=3, read=10))
    client, transport = _client(config=config)
    await client.get("/x", timeout=2.5)
    assert transport.last.extensions.timeout == Timeout(
        total=2.5,
        connect=3,
        read=10,
        write=30,
        pool=5,
    )


@pytest.mark.asyncio
async def test_merge_timeout_unset_keeps_config() -> None:
    config = _config(timeout=Timeout(total=8, connect=2))
    client, transport = _client(config=config)
    await client.get("/x", timeout=UNSET)
    assert transport.last.extensions.timeout == config.timeout


@pytest.mark.asyncio
async def test_merge_timeout_none_total_only() -> None:
    config = _config(timeout=Timeout(total=8, connect=2, read=7))
    client, transport = _client(config=config)
    await client.get("/x", timeout=None)
    effective = transport.last.extensions.timeout
    assert effective.total is None
    assert effective.connect == 2
    assert effective.read == 7


@pytest.mark.asyncio
async def test_merge_timeout_object_replaces_wholesale() -> None:
    override = Timeout(total=1, connect=1, read=1, write=1, pool=1)
    client, transport = _client()
    await client.get("/x", timeout=override)
    assert transport.last.extensions.timeout is override


@pytest.mark.asyncio
async def test_stream_default_timeout_total_none() -> None:
    client, transport = _client()
    async with client.stream("GET", "/x") as response:
        assert response.status == 200
        assert transport.last.extensions.timeout.total is None


@pytest.mark.asyncio
async def test_merge_retry_unset_keeps_config() -> None:
    config = _config(retry=RetryConfig(max_attempts=4))
    client, transport = _client(config=config)
    await client.get("/x", retry=UNSET)
    assert transport.last.extensions.retry == config.retry


@pytest.mark.asyncio
async def test_merge_retry_none_disables() -> None:
    client, transport = _client()
    await client.get("/x", retry=None)
    assert transport.last.extensions.retry is None


@pytest.mark.asyncio
async def test_merge_retry_object_replaces() -> None:
    override = RetryConfig(max_attempts=7)
    client, transport = _client()
    await client.get("/x", retry=override)
    assert transport.last.extensions.retry is override


@pytest.mark.asyncio
async def test_merge_follow_redirects_overrides_follow() -> None:
    config = _config(
        redirects=RedirectConfig(
            follow=False,
            max_redirects=9,
            strip_auth_on_origin_change=False,
        )
    )
    client, transport = _client(config=config)
    await client.get("/x", follow_redirects=True)
    redirects = transport.last.extensions.redirects
    assert redirects.follow is True
    assert redirects.max_redirects == 9
    assert redirects.strip_auth_on_origin_change is False


@pytest.mark.asyncio
async def test_auth_override_written_to_extensions() -> None:
    client, transport = _client()
    await client.get("/x", auth=UNSET)
    assert transport.last.extensions.auth_override is UNSET
    await client.get("/x", auth=None)
    assert transport.last.extensions.auth_override is None
    policy = _AuthPolicy()
    await client.get("/x", auth=policy)
    assert transport.last.extensions.auth_override is policy


@pytest.mark.asyncio
async def test_extensions_writers_and_override_hierarchy() -> None:
    client, transport = _client(name="billing")
    await client.get("/users/{id}", path_params={"id": 1}, timeout=4.0)
    extensions = transport.last.extensions
    assert extensions.upstream == "billing"
    assert extensions.endpoint == "/users/{id}"
    assert extensions.idempotent is True
    assert extensions.timeout.total == 4.0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "expected"),
    [
        ("GET", True),
        ("HEAD", True),
        ("PUT", True),
        ("DELETE", True),
        ("OPTIONS", True),
        ("TRACE", True),
        ("POST", False),
        ("PATCH", False),
    ],
)
async def test_idempotent_by_method(method: str, expected: bool) -> None:
    client, transport = _client()
    await client.request(method, "/x")
    assert transport.last.extensions.idempotent is expected


@pytest.mark.asyncio
async def test_request_id_from_contextvar() -> None:
    token = rapidy_client_request_id.set("rid-1")
    try:
        client, transport = _client()
        await client.get("/x")
        assert transport.last.extensions.request_id == "rid-1"
    finally:
        rapidy_client_request_id.reset(token)


@pytest.mark.asyncio
async def test_deadline_from_arg_and_contextvar() -> None:
    clock = _FakeClock()
    token = rapidy_client_deadline.set(2.0)
    try:
        client, transport = _client(_clock=clock)
        await client.get("/context")
        assert transport.last.extensions.deadline == 102.0
        await client.get("/argument", deadline=5.0)
        assert transport.last.extensions.deadline == 105.0
    finally:
        rapidy_client_deadline.reset(token)


@pytest.mark.asyncio
async def test_json_body_encoded_via_encoders() -> None:
    client, transport = _client()
    await client.post("/x", json={"a": 1})
    assert transport.last.content == b'{"a": 1}'
    assert transport.last.headers.get("content-type") == "application/json"


@pytest.mark.asyncio
async def test_data_form_urlencoded() -> None:
    client, transport = _client()
    await client.post("/x", data={"z": "last", "a": "first"})
    assert transport.last.content == b"a=first&z=last"
    assert (
        transport.last.headers.get("content-type")
        == "application/x-www-form-urlencoded"
    )


@pytest.mark.asyncio
async def test_query_serialization_defaults() -> None:
    client, transport = _client()
    await client.get(
        "/x",
        query={"tag": ["a", "b"], "flag": True, "skip": None},
    )
    raw = transport.last.url._raw_str()
    assert "tag=a&tag=b&flag=true" in raw
    assert "skip" not in raw


@pytest.mark.asyncio
async def test_path_params_url_escaped() -> None:
    client, transport = _client()
    await client.get("/u/{id}", path_params={"id": "a/b"})
    assert "/u/a%2Fb" in transport.last.url._raw_str()


@pytest.mark.asyncio
async def test_absolute_url_blocked() -> None:
    client, _ = _client()
    with pytest.raises(ValueError, match="absolute"):
        await client.get("https://evil.example.com")


@pytest.mark.asyncio
async def test_multiple_bodies_raises() -> None:
    client, _ = _client()
    with pytest.raises(ValueError, match="body"):
        await client.post("/x", json={"a": 1}, content=b"body")


@pytest.mark.asyncio
async def test_files_not_implemented_yet() -> None:
    client, _ = _client()
    with pytest.raises(NotImplementedError, match="18"):
        await client.post("/x", files=[FilePart(name="f", content=b"x")])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("shortcut", "method"),
    [
        ("get", "GET"),
        ("post", "POST"),
        ("put", "PUT"),
        ("patch", "PATCH"),
        ("delete", "DELETE"),
        ("head", "HEAD"),
        ("options", "OPTIONS"),
    ],
)
async def test_shortcuts_delegate_method(shortcut: str, method: str) -> None:
    client, transport = _client()
    await getattr(client, shortcut)("/x")
    assert transport.last.method == method


@pytest.mark.asyncio
async def test_raise_for_status_raises_status_error() -> None:
    transport = _RecordingTransport(status=404, body=b"missing")
    client, _ = _client(transport=transport)
    with pytest.raises(StatusError) as error:
        await client.get("/x")
    assert error.value.status == 404
    assert error.value.response is not None
    assert await error.value.response.aread() == b"missing"


@pytest.mark.asyncio
async def test_raise_for_status_false_returns_response() -> None:
    client, _ = _client(transport=_RecordingTransport(status=500))
    response = await client.get("/x", raise_for_status=False)
    assert response.status == 500


@pytest.mark.asyncio
async def test_status_error_not_seen_by_middleware() -> None:
    spy = _StatusSpy()
    client, _ = _client(
        transport=_RecordingTransport(status=503),
        middlewares=(spy,),
    )
    with pytest.raises(StatusError):
        await client.get("/x")
    assert spy.statuses == [503]


@pytest.mark.asyncio
async def test_new_request_after_closing_raises() -> None:
    client, _ = _client()
    await client.aclose()
    with pytest.raises(ClientClosedError):
        await client.get("/x")
    with pytest.raises(ClientClosedError):
        client.ws("/ws")
    with pytest.raises(ClientClosedError):
        client.sse("/events")


@pytest.mark.asyncio
async def test_normal_request_drains(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = _BlockingTransport()
    monkeypatch.setattr(client_module, "HttpxTransport", lambda **kwargs: transport)
    client = HttpClient(_config())
    request_task = asyncio.create_task(client.get("/x"))
    await transport.entered.wait()
    close_task = asyncio.create_task(client.aclose(drain_timeout=1.0))
    await asyncio.sleep(0)
    assert close_task.done() is False
    transport.release.set()
    assert (await request_task).status == 200
    await close_task
    assert transport.log == ["complete", "close"]


@pytest.mark.asyncio
async def test_finite_stream_drains_until_context_exits() -> None:
    client, _ = _client()
    entered = asyncio.Event()
    release = asyncio.Event()

    async def consume() -> None:
        async with client.stream("GET", "/stream"):
            entered.set()
            await release.wait()

    consumer = asyncio.create_task(consume())
    await entered.wait()
    close_task = asyncio.create_task(client.aclose(drain_timeout=1.0))
    await asyncio.sleep(0)
    assert close_task.done() is False
    release.set()
    await consumer
    await close_task


@pytest.mark.asyncio
async def test_shutdown_infinite_stream_closed_immediately() -> None:
    client, _ = _client()
    infinite = _FakeInfinite()
    client._infinite.add(infinite)
    started = asyncio.get_running_loop().time()
    await client.aclose(drain_timeout=10.0)
    elapsed = asyncio.get_running_loop().time() - started
    assert infinite.closed.is_set()
    assert elapsed < 0.1


@pytest.mark.asyncio
async def test_drain_then_cancel_order(monkeypatch: pytest.MonkeyPatch) -> None:
    log: list[str] = []
    transport = _BlockingTransport(log)
    monkeypatch.setattr(client_module, "HttpxTransport", lambda **kwargs: transport)
    client = HttpClient(_config())
    request_task = asyncio.create_task(client.get("/x"))
    await transport.entered.wait()

    await client.aclose(drain_timeout=0.01)

    with pytest.raises(ClientClosedError):
        await request_task
    assert log == ["cancel", "close"]


@pytest.mark.asyncio
async def test_idempotent_aclose(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = _RecordingTransport()
    monkeypatch.setattr(client_module, "HttpxTransport", lambda **kwargs: transport)
    client = HttpClient(_config())
    await client.aclose()
    await client.aclose()
    assert transport.closes == 1


@pytest.mark.asyncio
async def test_external_transport_not_closed_ownership() -> None:
    client, transport = _client()
    assert client._owns_transport is False
    await client.aclose()
    assert transport.closes == 0


@pytest.mark.asyncio
async def test_owned_transport_closed_owns_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = _RecordingTransport()
    monkeypatch.setattr(client_module, "HttpxTransport", lambda **kwargs: transport)
    client = HttpClient(_config())
    assert client._owns_transport is True
    await client.aclose()
    assert transport.closes == 1


def test_loop_affinity_cross_loop_raises() -> None:
    client, _ = _client()
    asyncio.run(client.get("/first"))
    with pytest.raises(RuntimeError, match="event loop"):
        asyncio.run(client.get("/second"))


def test_loop_affinity_lazy_no_bind_on_construct() -> None:
    client, _ = _client()
    assert client._loop is None


@pytest.mark.asyncio
async def test_simple_context_closes() -> None:
    async with HttpClient.simple("https://simple.example.com") as client:
        assert client._closed is False
        assert client._loop is None
    assert client._closed is True


def test_client_facade_reexport() -> None:
    assert HttpClient.__module__ == "rapidy_client._client"
