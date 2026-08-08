from __future__ import annotations

from typing import Any

import pytest
from rapidy_client import HttpClient
from rapidy_client._models import (
    AttemptOutcome,
    CallNext,
    Headers,
    Request,
    Response,
    ResponseExtensions,
)
from rapidy_client.config import UpstreamConfig
from rapidy_client.errors import DeadlineExceededError
from rapidy_client.observability import BaseObserver, RequestContext
from rapidy_client.testing import FakeClock, MockTransport


class _RecordingClock(FakeClock):
    def __init__(self, events: list[str]) -> None:
        super().__init__()
        self.events = events
        self.sleeps: list[float] = []

    async def sleep(self, delay: float) -> None:
        self.events.append("sleep")
        self.sleeps.append(delay)
        await super().sleep(delay)


class _Observer(BaseObserver):
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.retries: list[dict[str, object]] = []

    async def on_retry(
        self,
        ctx: RequestContext,
        attempt: int,
        reason: str,
        delay: float,
    ) -> None:
        self.events.append("retry")
        self.retries.append({"attempt": attempt, "reason": reason, "delay": delay})


class _Listener:
    def __init__(self) -> None:
        self.outcomes: list[AttemptOutcome] = []

    def on_attempt(self, outcome: AttemptOutcome) -> None:
        self.outcomes.append(dict(outcome))


class _AttachListener:
    def __init__(self, listener: _Listener) -> None:
        self.listener = listener

    async def __call__(self, request: Request, call_next: CallNext) -> Response:
        request.extensions.attempt_listeners.append(self.listener)
        return await call_next(request)


def _response_503(
    request: Request,
    *,
    on_close: Any,
) -> Response:
    return Response(
        status=503,
        headers=Headers({"Retry-After": "2"}),
        request=request,
        extensions=ResponseExtensions(
            elapsed=0.0,
            attempt=request.extensions.attempt,
        ),
        on_close=on_close,
    )


def _config() -> UpstreamConfig:
    return UpstreamConfig.model_validate(
        {
            "base_url": "https://mock.test",
            "timeout": {"total": 10.0, "connect": 3.0},
        }
    )


@pytest.mark.asyncio
async def test_golden_retry_503_stepwise() -> None:
    events: list[str] = []
    headers_seen: list[str | None] = []
    clock = _RecordingClock(events)
    observer = _Observer(events)
    listener = _Listener()
    mock = MockTransport()

    async def close() -> None:
        events.append("close")

    async def first(request: Request) -> Response:
        headers_seen.append(request.headers.get("x-rapidy-deadline-ms"))
        return _response_503(request, on_close=close)

    async def second(request: Request) -> Response:
        headers_seen.append(request.headers.get("x-rapidy-deadline-ms"))
        return Response(
            status=200,
            headers=Headers(),
            request=request,
            extensions=ResponseExtensions(
                elapsed=0.0,
                attempt=request.extensions.attempt,
            ),
        )

    mock.route("GET", "/inv/1").times(1).respond_with(first).then().respond_with(second)
    client = HttpClient(
        _config(),
        transport=mock,
        middlewares=(_AttachListener(listener),),
        observers=(observer,),
        _clock=clock,
    )
    try:
        response = await client.get("/inv/1", deadline=10.0)
    finally:
        await client.aclose()

    assert mock.calls[0].response is not None
    assert mock.calls[0].response.status == 503
    assert events.index("close") < events.index("sleep")
    assert events.index("retry") < events.index("sleep")
    assert [outcome["status"] for outcome in listener.outcomes] == [503, 200]
    assert observer.retries == [{"attempt": 1, "reason": "status_503", "delay": 2.0}]
    assert clock.sleeps == [2.0]
    assert headers_seen == ["10000", "8000"]
    assert response.status == 200
    assert response.extensions.attempt == 2
    mock.assert_called("GET", "/inv/1", times=2)


@pytest.mark.asyncio
async def test_golden_retry_503_deadline_lt_connect_no_attempt2() -> None:
    events: list[str] = []
    clock = _RecordingClock(events)
    mock = MockTransport()

    async def close() -> None:
        events.append("close")

    async def first(request: Request) -> Response:
        return _response_503(request, on_close=close)

    mock.route("GET", "/inv/1").times(1).respond_with(first).then().respond(status=200)
    client = HttpClient(_config(), transport=mock, _clock=clock)
    try:
        with pytest.raises(DeadlineExceededError):
            await client.get("/inv/1", deadline=4.0)
    finally:
        await client.aclose()

    assert clock.sleeps == [2.0]
    assert events == ["close", "sleep"]
    mock.assert_called("GET", "/inv/1", times=1)
