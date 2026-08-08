from __future__ import annotations

import asyncio

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from rapidy_client import HttpClient, Request, Response, UpstreamConfig
from rapidy_client.errors import DeadlineExceededError
from rapidy_client.testing import FakeClock, MockTransport


def _config(*, connect: float) -> UpstreamConfig:
    return UpstreamConfig.model_validate(
        {
            "base_url": "https://mock.test",
            "timeout": {"total": None, "connect": connect},
            "retry": {"max_attempts": 2, "budget_ratio": None},
            "log": {"level": "off"},
        }
    )


@settings(max_examples=30, deadline=None)
@given(
    remaining=st.floats(
        min_value=0.1,
        max_value=20.0,
        allow_nan=False,
        allow_infinity=False,
    ),
    delay=st.integers(min_value=0, max_value=20),
)
def test_retry_sleep_is_capped_by_remaining(remaining: float, delay: int) -> None:
    async def scenario() -> None:
        clock = FakeClock()
        mock = MockTransport()
        headers_seen: list[int] = []

        async def first(request: Request) -> Response:
            headers_seen.append(int(request.headers["x-rapidy-deadline-ms"]))
            return mock_response(request, status=503, retry_after=str(delay))

        mock.route("GET", "/deadline").times(1).respond_with(first).then().respond()
        client = HttpClient(_config(connect=0.05), transport=mock, _clock=clock)
        try:
            try:
                await client.get("/deadline", deadline=remaining)
            except DeadlineExceededError:
                pass
        finally:
            await client.aclose()

        assert clock.monotonic() == pytest.approx(min(float(delay), remaining))
        assert headers_seen == [int(remaining * 1000)]

    asyncio.run(scenario())


@settings(max_examples=30, deadline=None)
@given(
    connect=st.floats(
        min_value=0.1,
        max_value=10.0,
        allow_nan=False,
        allow_infinity=False,
    ),
    ratio=st.floats(
        min_value=0.0,
        max_value=0.999,
        allow_nan=False,
        allow_infinity=False,
    ),
)
def test_remaining_below_connect_starts_no_attempt(
    connect: float,
    ratio: float,
) -> None:
    async def scenario() -> None:
        mock = MockTransport()
        mock.route("GET", "/deadline").respond()
        client = HttpClient(
            _config(connect=connect),
            transport=mock,
            _clock=FakeClock(),
        )
        try:
            with pytest.raises(DeadlineExceededError):
                await client.get("/deadline", deadline=connect * ratio)
        finally:
            await client.aclose()

        assert mock.calls == []

    asyncio.run(scenario())


def mock_response(request: Request, *, status: int, retry_after: str) -> Response:
    from rapidy_client import Headers, ResponseExtensions

    return Response(
        status=status,
        headers=Headers({"retry-after": retry_after}),
        request=request,
        extensions=ResponseExtensions(
            elapsed=0.0,
            attempt=request.extensions.attempt,
        ),
    )
