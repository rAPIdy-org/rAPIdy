from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import pytest
from rapidy_client import (
    UNSET,
    URL,
    ConnectError,
    Headers,
    HttpClient,
    Request,
    RequestExtensions,
    Response,
    ResponseExtensions,
    StatusError,
    Timeout,
    UpstreamConfig,
)
from rapidy_client.config import LogConfig
from rapidy_client.observability import (
    BaseObserver,
    LoggingObserver,
    RequestContext,
    notify_observers,
)


async def _stream(body: bytes) -> AsyncIterator[bytes]:
    if body:
        yield body


def _request(
    *,
    headers: Headers | None = None,
    content: bytes | None = None,
    url: str = "https://example.test/x?token=SECRET",
) -> Request:
    return Request(
        method="GET",
        url=URL(url),
        headers=headers or Headers(),
        content=content,
        extensions=RequestExtensions(
            upstream="catalog",
            endpoint="/x",
            request_id="request-1",
            timeout=Timeout(),
            retry=None,
            idempotent=True,
            auth_override=UNSET,
            deadline=None,
            redirects=None,  # type: ignore[arg-type]
        ),
    )


def _response(
    *,
    status: int = 200,
    body: bytes = b"ok",
    request: Request | None = None,
    headers: Headers | None = None,
) -> Response:
    return Response(
        status=status,
        headers=headers or Headers(),
        request=request or _request(),
        extensions=ResponseExtensions(elapsed=0.01, attempt=2),
        stream=_stream(body),
    )


def _context(**overrides: Any) -> RequestContext:
    values: dict[str, Any] = {
        "upstream": "catalog",
        "method": "GET",
        "endpoint": "/x",
        "url": URL("https://example.test/x?token=SECRET"),
        "attempt": 2,
        "request_id": "request-1",
        "started_at": 10.0,
        "elapsed": 0.125,
    }
    values.update(overrides)
    return RequestContext(**values)


class _StubTransport:
    def __init__(self, *, status: int = 200, body: bytes = b"ok") -> None:
        self.status = status
        self.body = body
        self.error: Exception | None = None

    async def handle(self, request: Request) -> Response:
        if self.error is not None:
            raise self.error
        return _response(status=self.status, body=self.body, request=request)

    async def aclose(self) -> None:
        return None


class _SpyObserver(BaseObserver):
    def __init__(self) -> None:
        self.events: list[tuple[str, RequestContext, object | None]] = []

    async def on_request_start(self, ctx: RequestContext) -> None:
        self.events.append(("start", ctx, None))

    async def on_request_end(
        self,
        ctx: RequestContext,
        response: Response,
    ) -> None:
        self.events.append(("end", ctx, response))

    async def on_request_error(
        self,
        ctx: RequestContext,
        exc: Exception,
    ) -> None:
        self.events.append(("error", ctx, exc))


@pytest.mark.asyncio
async def test_base_observer_all_hooks_noop() -> None:
    observer = BaseObserver()
    ctx = _context()
    response = _response()
    assert await observer.on_request_start(ctx) is None
    assert await observer.on_request_end(ctx, response) is None
    assert await observer.on_request_error(ctx, ConnectError()) is None
    assert await observer.on_attempt_start(ctx) is None
    assert await observer.on_attempt_end(ctx, response, None) is None
    assert await observer.on_retry(ctx, 2, "status_503", 0.1) is None
    assert await observer.on_breaker_transition("u", "closed", "open") is None
    assert await observer.on_pool_wait("u", 0.1) is None
    assert await observer.on_connection_open("u", False, 0.0, 0.1) is None


def test_request_context_is_frozen_and_repr_redacts_url() -> None:
    ctx = _context()
    with pytest.raises(dataclasses.FrozenInstanceError):
        ctx.attempt = 5  # type: ignore[misc]
    assert "SECRET" not in repr(ctx)
    assert "redacted" in repr(ctx)


@pytest.mark.asyncio
async def test_notify_observers_swallows_exception_and_continues(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class BadObserver(BaseObserver):
        async def on_request_start(self, ctx: RequestContext) -> None:
            del ctx
            raise RuntimeError("boom")

    good = _SpyObserver()
    with caplog.at_level(logging.ERROR, logger="rapidy_client.observability"):
        await notify_observers([BadObserver(), good], "on_request_start", _context())
    assert [event[0] for event in good.events] == ["start"]
    assert any("request continues" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_notify_observers_reraises_cancelled() -> None:
    class CancelledObserver(BaseObserver):
        async def on_request_start(self, ctx: RequestContext) -> None:
            del ctx
            raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await notify_observers(
            [CancelledObserver()],
            "on_request_start",
            _context(),
        )


@pytest.mark.asyncio
async def test_notify_observers_skips_missing_hook() -> None:
    class PartialObserver:
        async def on_request_start(self, ctx: RequestContext) -> None:
            del ctx

    await notify_observers(  # type: ignore[arg-type]
        [PartialObserver()],
        "on_pool_wait",
        "catalog",
        0.1,
    )


def _payload(caplog: pytest.LogCaptureFixture) -> dict[str, Any]:
    records = [record for record in caplog.records if record.name == "test.http"]
    assert len(records) == 1
    return json.loads(records[0].message)  # type: ignore[no-any-return]


@pytest.mark.asyncio
async def test_logging_observer_off_is_silent(
    caplog: pytest.LogCaptureFixture,
) -> None:
    logger = logging.getLogger("test.http")
    observer = LoggingObserver(LogConfig(level="off"), logger=logger)
    with caplog.at_level(logging.INFO, logger="test.http"):
        await observer.on_request_end(_context(), _response())
    assert not [record for record in caplog.records if record.name == "test.http"]


@pytest.mark.asyncio
async def test_logging_observer_meta_writes_one_event(
    caplog: pytest.LogCaptureFixture,
) -> None:
    observer = LoggingObserver(
        LogConfig(level="meta"),
        logger=logging.getLogger("test.http"),
    )
    with caplog.at_level(logging.INFO, logger="test.http"):
        await observer.on_request_end(_context(), _response())
    payload = _payload(caplog)
    assert payload["event"] == "http_request"
    assert payload["status"] == 200
    assert payload["duration_ms"] == 125.0
    assert "request_headers" not in payload
    assert "response_body" not in payload
    assert "SECRET" not in json.dumps(payload)


@pytest.mark.asyncio
async def test_logging_observer_headers_redacts_defaults_and_extras(
    caplog: pytest.LogCaptureFixture,
) -> None:
    request = _request(
        headers=Headers(
            {
                "Authorization": "Bearer HEADER_SECRET",
                "X-Tenant": "TENANT_SECRET",
            }
        ),
        url=(
            "https://USER_SECRET:PASS_SECRET@example.test/x?api_key=QUERY_SECRET"
            "&access_token=ACCESS_SECRET&password=PASSWORD_SECRET&tenant=QUERY_EXTRA"
        ),
    )
    response = _response(request=request)
    observer = LoggingObserver(
        LogConfig(
            level="headers",
            redact_headers_extra=frozenset({"x-tenant"}),
            redact_query_extra=frozenset({"tenant"}),
        ),
        logger=logging.getLogger("test.http"),
    )
    with caplog.at_level(logging.INFO, logger="test.http"):
        await observer.on_request_end(_context(url=request.url), response)
    rendered = json.dumps(_payload(caplog))
    assert "HEADER_SECRET" not in rendered
    assert "TENANT_SECRET" not in rendered
    assert "QUERY_SECRET" not in rendered
    assert "USER_SECRET" not in rendered
    assert "PASS_SECRET" not in rendered
    assert "ACCESS_SECRET" not in rendered
    assert "PASSWORD_SECRET" not in rendered
    assert "QUERY_EXTRA" not in rendered


@pytest.mark.asyncio
async def test_logging_observer_body_crops_and_redacts(
    caplog: pytest.LogCaptureFixture,
) -> None:
    response = _response(body=b'{"token": "BODY_SECRET"}' + b"x" * 100)
    await response.aread()
    observer = LoggingObserver(
        LogConfig(level="body", max_body_len=40),
        logger=logging.getLogger("test.http"),
    )
    with caplog.at_level(logging.INFO, logger="test.http"):
        await observer.on_request_end(_context(), response)
    payload = _payload(caplog)
    assert "BODY_SECRET" not in str(payload["response_body"])
    assert str(payload["response_body"]).endswith("…(cropped)")


@pytest.mark.asyncio
async def test_logging_observer_error_logs_only_exception_type(
    caplog: pytest.LogCaptureFixture,
) -> None:
    observer = LoggingObserver(
        LogConfig(level="meta"),
        logger=logging.getLogger("test.http"),
    )
    with caplog.at_level(logging.INFO, logger="test.http"):
        await observer.on_request_error(
            _context(),
            ConnectError("Authorization: ERROR_SECRET"),
        )
    payload = _payload(caplog)
    assert payload["error"] == "ConnectError"
    assert payload["status"] is None
    assert "ERROR_SECRET" not in json.dumps(payload)


@pytest.mark.asyncio
async def test_client_enables_logging_observer_by_default(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = HttpClient(
        UpstreamConfig(base_url="https://example.test"),
        transport=_StubTransport(),
    )
    with caplog.at_level(logging.INFO, logger="rapidy_client.http"):
        await client.get("/x")
    records = [
        record for record in caplog.records if record.name == "rapidy_client.http"
    ]
    assert len(records) == 1
    assert json.loads(records[0].message)["event"] == "http_request"


def _client(
    transport: _StubTransport,
    observer: BaseObserver,
) -> HttpClient:
    return HttpClient(
        UpstreamConfig.model_validate(
            {
                "base_url": "https://example.test",
                "log": {"level": "off"},
            }
        ),
        name="catalog",
        transport=transport,
        observers=[observer],
    )


@pytest.mark.asyncio
async def test_request_invokes_start_then_end() -> None:
    observer = _SpyObserver()
    response = await _client(_StubTransport(), observer).get("/x")
    assert response.status == 200
    assert [event[0] for event in observer.events] == ["start", "end"]
    assert observer.events[0][1].upstream == "catalog"
    assert observer.events[0][1].endpoint == "/x"
    assert observer.events[1][2] is response


@pytest.mark.asyncio
async def test_request_error_invokes_error_hook() -> None:
    observer = _SpyObserver()
    transport = _StubTransport()
    transport.error = ConnectError("boom")
    with pytest.raises(ConnectError):
        await _client(transport, observer).get("/x")
    assert [event[0] for event in observer.events] == ["start", "error"]


@pytest.mark.asyncio
async def test_status_error_triggers_end_not_error() -> None:
    observer = _SpyObserver()
    with pytest.raises(StatusError):
        await _client(_StubTransport(status=503), observer).get("/x")
    assert [event[0] for event in observer.events] == ["start", "end"]
    response = observer.events[1][2]
    assert isinstance(response, Response)
    assert response.status == 503


@pytest.mark.asyncio
async def test_failing_observer_does_not_fail_request(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class BadObserver(BaseObserver):
        async def on_request_start(self, ctx: RequestContext) -> None:
            del ctx
            raise RuntimeError("boom")

    with caplog.at_level(logging.ERROR, logger="rapidy_client.observability"):
        response = await _client(_StubTransport(), BadObserver()).get("/x")
    assert response.status == 200
    assert any("request continues" in record.message for record in caplog.records)
