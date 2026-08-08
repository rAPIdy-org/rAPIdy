from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from rapidy_client._models import (
    URL,
    AttemptOutcome,
    Headers,
    Request,
    RequestExtensions,
    Response,
    ResponseExtensions,
    Timeout,
)
from rapidy_client.config import RedirectConfig, RetryConfig
from rapidy_client.errors import (
    ConnectError,
    DeadlineExceededError,
    HttpTimeoutError,
    ServerDisconnectedError,
)
from rapidy_client.middleware.retry import RetryMiddleware
from rapidy_client.observability import BaseObserver, RequestContext
from rapidy_client.testing import FakeClock
from rapidy_core import UNSET


class _SpyObserver(BaseObserver):
    def __init__(self) -> None:
        self.retries: list[dict[str, object]] = []

    async def on_retry(
        self,
        ctx: RequestContext,
        attempt: int,
        reason: str,
        delay: float,
    ) -> None:
        self.retries.append(
            {
                "attempt": attempt,
                "reason": reason,
                "delay": delay,
                "upstream": ctx.upstream,
            }
        )


class _SpyListener:
    def __init__(self) -> None:
        self.outcomes: list[AttemptOutcome] = []

    def on_attempt(self, outcome: AttemptOutcome) -> None:
        self.outcomes.append(dict(outcome))


class _RecordingClock(FakeClock):
    def __init__(self, events: list[str] | None = None) -> None:
        super().__init__()
        self.sleeps: list[float] = []
        self.events = events

    async def sleep(self, delay: float) -> None:
        self.sleeps.append(delay)
        if self.events is not None:
            self.events.append("sleep")
        await super().sleep(delay)


def _request(
    *,
    method: str = "GET",
    retry: RetryConfig | None = None,
    idempotent: bool = True,
    deadline: float | None = None,
    listeners: list[_SpyListener] | None = None,
    content: Any = b"",
) -> Request:
    effective_retry = RetryConfig() if retry is None else retry
    return Request(
        method=method,
        url=URL("https://mock.test/x"),
        headers=Headers(),
        content=content,
        extensions=RequestExtensions(
            upstream="test",
            endpoint="/x",
            request_id="request-1",
            timeout=Timeout(),
            retry=effective_retry,
            idempotent=idempotent,
            auth_override=UNSET,
            deadline=deadline,
            redirects=RedirectConfig(),
            attempt_listeners=listeners or [],
        ),
    )


def _response(
    request: Request,
    status: int,
    *,
    headers: dict[str, str] | None = None,
    on_close: Any = None,
) -> Response:
    return Response(
        status=status,
        headers=Headers(headers),
        request=request,
        extensions=ResponseExtensions(
            elapsed=0.0,
            attempt=request.extensions.attempt,
        ),
        on_close=on_close,
    )


def _sequence(request: Request, *outcomes: Response | BaseException) -> Any:
    remaining = list(outcomes)

    async def call_next(_: Request) -> Response:
        outcome = remaining.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    return call_next


@pytest.mark.asyncio
async def test_status_503_retried_then_success() -> None:
    request = _request()
    clock = _RecordingClock()
    middleware = RetryMiddleware(RetryConfig(), clock=clock)

    result = await middleware(
        request,
        _sequence(request, _response(request, 503), _response(request, 200)),
    )

    assert result.status == 200
    assert len(clock.sleeps) == 1
    assert 0.0 <= clock.sleeps[0] <= 0.1


@pytest.mark.asyncio
async def test_post_not_retried() -> None:
    request = _request(method="POST", idempotent=False)
    calls = 0

    async def call_next(_: Request) -> Response:
        nonlocal calls
        calls += 1
        return _response(request, 503)

    clock = _RecordingClock()
    result = await RetryMiddleware(RetryConfig(), clock=clock)(request, call_next)

    assert result.status == 503
    assert calls == 1
    assert clock.sleeps == []


@pytest.mark.asyncio
async def test_declarative_idempotent_allows_post_retry() -> None:
    request = _request(method="POST", idempotent=True)

    result = await RetryMiddleware(RetryConfig(), clock=FakeClock())(
        request,
        _sequence(request, _response(request, 503), _response(request, 200)),
    )

    assert result.status == 200
    assert request.extensions.attempt == 2


@pytest.mark.asyncio
async def test_status_500_not_retryable_returns_immediately() -> None:
    request = _request()
    clock = _RecordingClock()

    result = await RetryMiddleware(RetryConfig(), clock=clock)(
        request,
        _sequence(request, _response(request, 500)),
    )

    assert result.status == 500
    assert clock.sleeps == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("86400", 30.0),
        ("Wed, 21 Oct 2099 07:28:00 GMT", 30.0),
    ],
)
async def test_retry_after_cap_and_http_date_future(
    value: str,
    expected: float,
) -> None:
    request = _request()
    clock = _RecordingClock()
    observer = _SpyObserver()

    result = await RetryMiddleware(
        RetryConfig(),
        clock=clock,
        observers=(observer,),
    )(
        request,
        _sequence(
            request,
            _response(request, 503, headers={"Retry-After": value}),
            _response(request, 200),
        ),
    )

    assert result.status == 200
    assert clock.sleeps == [expected]
    assert observer.retries[0]["delay"] == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "value",
    ["Thu, 01 Jan 1970 00:00:00 GMT", "soon-ish"],
)
async def test_retry_after_invalid_falls_back_to_backoff(value: str) -> None:
    request = _request()
    clock = _RecordingClock()

    result = await RetryMiddleware(RetryConfig(), clock=clock)(
        request,
        _sequence(
            request,
            _response(request, 503, headers={"Retry-After": value}),
            _response(request, 200),
        ),
    )

    assert result.status == 200
    assert len(clock.sleeps) == 1
    assert 0.0 <= clock.sleeps[0] <= 0.1


@pytest.mark.asyncio
async def test_budget_exhausted_returns_last_response() -> None:
    request = _request()
    clock = _RecordingClock()
    observer = _SpyObserver()
    middleware = RetryMiddleware(
        RetryConfig(budget_ratio=0.1),
        clock=clock,
        observers=(observer,),
    )
    middleware._budget = 0.0

    response = _response(request, 503)
    result = await middleware(request, _sequence(request, response))

    assert result is response
    assert clock.sleeps == []
    assert observer.retries == [
        {
            "attempt": 1,
            "reason": "budget_exhausted",
            "delay": 0.0,
            "upstream": "test",
        }
    ]


@pytest.mark.asyncio
async def test_failed_body_closed_before_sleep() -> None:
    request = _request()
    events: list[str] = []

    async def close() -> None:
        events.append("close")

    clock = _RecordingClock(events)
    result = await RetryMiddleware(RetryConfig(), clock=clock)(
        request,
        _sequence(
            request,
            _response(request, 503, on_close=close),
            _response(request, 200),
        ),
    )

    assert result.status == 200
    assert events == ["close", "sleep"]


@pytest.mark.asyncio
async def test_connect_error_retried() -> None:
    request = _request()
    observer = _SpyObserver()

    result = await RetryMiddleware(
        RetryConfig(),
        clock=FakeClock(),
        observers=(observer,),
    )(
        request,
        _sequence(request, ConnectError("lost"), _response(request, 200)),
    )

    assert result.status == 200
    assert observer.retries[0]["reason"] == "network_ConnectError"


@pytest.mark.asyncio
async def test_server_disconnected_retried() -> None:
    request = _request()
    observer = _SpyObserver()

    result = await RetryMiddleware(
        RetryConfig(),
        clock=FakeClock(),
        observers=(observer,),
    )(
        request,
        _sequence(
            request,
            ServerDisconnectedError("lost"),
            _response(request, 200),
        ),
    )

    assert result.status == 200
    assert observer.retries[0]["reason"] == "network_ServerDisconnectedError"


@pytest.mark.asyncio
async def test_network_error_non_idempotent_not_retried() -> None:
    request = _request(method="POST", idempotent=False)

    with pytest.raises(ConnectError, match="lost"):
        await RetryMiddleware(RetryConfig(), clock=FakeClock())(
            request,
            _sequence(request, ConnectError("lost")),
        )
    assert request.extensions.attempt == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [DeadlineExceededError("expired"), HttpTimeoutError("total", phase="total")],
)
async def test_deadline_and_total_timeout_not_retryable(error: Exception) -> None:
    request = _request()

    with pytest.raises(type(error)):
        await RetryMiddleware(RetryConfig(), clock=FakeClock())(
            request,
            _sequence(request, error),
        )
    assert request.extensions.attempt == 1


@pytest.mark.asyncio
async def test_attempt_listeners_notified_each_attempt() -> None:
    listener = _SpyListener()
    request = _request(listeners=[listener])

    result = await RetryMiddleware(RetryConfig(), clock=FakeClock())(
        request,
        _sequence(
            request,
            ConnectError("first"),
            _response(request, 503),
            _response(request, 200),
        ),
    )

    assert result.status == 200
    assert [outcome["status"] for outcome in listener.outcomes] == [None, 503, 200]
    assert isinstance(listener.outcomes[0]["exception"], ConnectError)
    assert all("elapsed" in outcome for outcome in listener.outcomes)


@pytest.mark.asyncio
async def test_non_replayable_not_retried() -> None:
    async def content() -> AsyncIterator[bytes]:
        yield b"one shot"

    request = _request(content=content())
    calls = 0

    async def call_next(_: Request) -> Response:
        nonlocal calls
        calls += 1
        return _response(request, 503)

    result = await RetryMiddleware(RetryConfig(), clock=FakeClock())(
        request,
        call_next,
    )

    assert result.status == 503
    assert calls == 1


@pytest.mark.asyncio
async def test_max_attempts_exhausted_returns_last() -> None:
    request = _request(retry=RetryConfig(max_attempts=3))
    clock = _RecordingClock()
    responses = [_response(request, 503) for _ in range(3)]

    result = await RetryMiddleware(RetryConfig(), clock=clock)(
        request,
        _sequence(request, *responses),
    )

    assert result is responses[-1]
    assert request.extensions.attempt == 3
    assert len(clock.sleeps) == 2


@pytest.mark.asyncio
async def test_retry_none_single_attempt_and_notifies_listener() -> None:
    listener = _SpyListener()
    request = _request(listeners=[listener])
    request.extensions.retry = None

    result = await RetryMiddleware(RetryConfig(), clock=FakeClock())(
        request,
        _sequence(request, _response(request, 503)),
    )

    assert result.status == 503
    assert request.extensions.attempt == 1
    assert [outcome["status"] for outcome in listener.outcomes] == [503]


@pytest.mark.asyncio
async def test_per_attempt_handler_sees_incremented_attempt() -> None:
    request = _request()
    seen: list[int] = []
    responses = [
        _response(request, 503),
        _response(request, 503),
        _response(request, 200),
    ]

    async def call_next(current: Request) -> Response:
        seen.append(current.extensions.attempt)
        return responses.pop(0)

    result = await RetryMiddleware(RetryConfig(), clock=FakeClock())(
        request,
        call_next,
    )

    assert result.status == 200
    assert seen == [1, 2, 3]
