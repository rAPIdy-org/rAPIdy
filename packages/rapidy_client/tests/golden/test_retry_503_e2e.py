from __future__ import annotations

import asyncio
from typing import Any

import pytest
from rapidy_client import (
    Headers,
    HttpClient,
    Request,
    Response,
    ResponseExtensions,
    UpstreamConfig,
)
from rapidy_client.errors import DeadlineExceededError
from rapidy_client.observability import BaseObserver, RequestContext
from rapidy_client.testing import FakeClock, MockTransport


class _EventClock(FakeClock):
    def __init__(self, events: list[str]) -> None:
        super().__init__()
        self.events = events

    async def sleep(self, delay: float) -> None:
        self.events.append("sleep")
        await super().sleep(delay)


class _RetrySpy(BaseObserver):
    def __init__(self) -> None:
        self.retries: list[dict[str, object]] = []

    async def on_retry(
        self,
        ctx: RequestContext,
        attempt: int,
        reason: str,
        delay: float,
    ) -> None:
        del ctx
        self.retries.append({"attempt": attempt, "reason": reason, "delay": delay})


def _response_503(request: Request, *, on_close: Any) -> Response:
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
            "timeout": {"total": 100.0, "connect": 3.0},
            "log": {"level": "off"},
        }
    )


@pytest.mark.asyncio
async def test_retry_503_full_trace_without_real_sleep() -> None:
    events: list[str] = []
    deadline_headers: list[int] = []
    clock = _EventClock(events)
    observer = _RetrySpy()
    mock = MockTransport()

    async def close() -> None:
        events.append("close")

    async def first(request: Request) -> Response:
        deadline_headers.append(int(request.headers["x-rapidy-deadline-ms"]))
        return _response_503(request, on_close=close)

    async def second(request: Request) -> Response:
        deadline_headers.append(int(request.headers["x-rapidy-deadline-ms"]))
        return Response(
            status=200,
            headers=Headers(),
            request=request,
            extensions=ResponseExtensions(
                elapsed=0.0,
                attempt=request.extensions.attempt,
            ),
        )

    mock.route("GET", "/pay").times(1).respond_with(first).then().respond_with(second)
    client = HttpClient(
        _config(),
        transport=mock,
        observers=(observer,),
        _clock=clock,
    )
    try:
        async with asyncio.timeout(0.5):
            response = await client.get("/pay", deadline=100.0)
    finally:
        await client.aclose()

    assert len(mock.calls) == 2
    assert mock.calls[0].response is not None
    assert mock.calls[0].response.status == 503
    assert events.index("close") < events.index("sleep")
    assert observer.retries == [{"attempt": 1, "reason": "status_503", "delay": 2.0}]
    assert clock.monotonic() == pytest.approx(2.0)
    assert mock.calls[1].request.extensions.attempt == 2
    assert response.status == 200
    assert deadline_headers == [100000, 98000]
    assert all("traceparent" not in call.request.headers for call in mock.calls)


@pytest.mark.asyncio
async def test_retry_503_remaining_below_connect_starts_no_second_attempt() -> None:
    events: list[str] = []
    clock = _EventClock(events)
    mock = MockTransport()

    async def close() -> None:
        events.append("close")

    async def first(request: Request) -> Response:
        return _response_503(request, on_close=close)

    mock.route("GET", "/pay").times(1).respond_with(first).then().respond(status=200)
    client = HttpClient(_config(), transport=mock, _clock=clock)
    try:
        with pytest.raises(DeadlineExceededError):
            await client.get("/pay", deadline=4.0)
    finally:
        await client.aclose()

    assert clock.monotonic() == pytest.approx(2.0)
    assert events == ["close", "sleep"]
    mock.assert_called("GET", "/pay", times=1)
