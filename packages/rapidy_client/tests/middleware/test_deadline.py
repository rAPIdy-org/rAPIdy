from __future__ import annotations

import pytest
from rapidy_client import HttpClient
from rapidy_client._models import (
    URL,
    Headers,
    Request,
    RequestExtensions,
    Response,
    ResponseExtensions,
    Timeout,
)
from rapidy_client.config import DeadlineConfig, RedirectConfig, UpstreamConfig
from rapidy_client.errors import DeadlineExceededError
from rapidy_client.middleware.deadline import DeadlineMiddleware
from rapidy_client.testing import FakeClock, MockTransport
from rapidy_core import UNSET


def _request(
    *,
    deadline: float | None,
    timeout: Timeout | None = None,
    headers: Headers | None = None,
) -> Request:
    return Request(
        method="GET",
        url=URL("https://mock.test/x"),
        headers=headers or Headers(),
        content=b"",
        extensions=RequestExtensions(
            upstream="billing",
            endpoint="/x",
            request_id="request-1",
            timeout=timeout or Timeout(),
            retry=None,
            idempotent=True,
            auth_override=UNSET,
            deadline=deadline,
            redirects=RedirectConfig(),
        ),
    )


def _response(request: Request) -> Response:
    return Response(
        status=200,
        headers=Headers(),
        request=request,
        extensions=ResponseExtensions(elapsed=0.0, attempt=0),
    )


@pytest.mark.asyncio
async def test_header_injected_ms_and_replaced() -> None:
    clock = FakeClock(start=100.0)
    request = _request(
        deadline=105.0,
        headers=Headers(
            [
                ("X-Rapidy-Deadline-Ms", "old"),
                ("x-rapidy-deadline-ms", "duplicate"),
            ]
        ),
    )

    async def call_next(current: Request) -> Response:
        assert current.headers.get_all("x-rapidy-deadline-ms") == ["5000"]
        return _response(current)

    await DeadlineMiddleware(DeadlineConfig(), clock=clock)(request, call_next)


@pytest.mark.asyncio
async def test_propagate_false_does_not_add_header() -> None:
    request = _request(deadline=5.0)

    async def call_next(current: Request) -> Response:
        assert "x-rapidy-deadline-ms" not in current.headers
        return _response(current)

    await DeadlineMiddleware(
        DeadlineConfig(propagate=False),
        clock=FakeClock(),
    )(request, call_next)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("total", "expected"),
    [(10.0, 4.0), (None, 4.0)],
)
async def test_total_capped_by_remaining(
    total: float | None,
    expected: float,
) -> None:
    request = _request(deadline=4.0, timeout=Timeout(total=total, connect=3.0))

    async def call_next(current: Request) -> Response:
        assert current.extensions.timeout.total == expected
        assert current.extensions.timeout.connect == 3.0
        return _response(current)

    await DeadlineMiddleware(DeadlineConfig(), clock=FakeClock())(request, call_next)


@pytest.mark.asyncio
async def test_no_attempt_when_remaining_lt_connect() -> None:
    mock = MockTransport()
    client = HttpClient(
        UpstreamConfig.model_validate(
            {
                "base_url": "https://mock.test",
                "timeout": {"connect": 3.0},
            }
        ),
        transport=mock,
        _clock=FakeClock(),
    )

    with pytest.raises(DeadlineExceededError, match="before attempt"):
        await client.get("/x", deadline=1.0)

    assert mock.calls == []
    await client.aclose()


@pytest.mark.asyncio
async def test_sleep_capped_by_remaining() -> None:
    clock = FakeClock()
    mock = MockTransport()
    mock.route("GET", "/x").respond(
        status=503,
        headers={"Retry-After": "10"},
    ).then().respond(status=200)
    client = HttpClient(
        UpstreamConfig.model_validate(
            {
                "base_url": "https://mock.test",
                "timeout": {"connect": 3.0},
            }
        ),
        transport=mock,
        _clock=clock,
    )

    with pytest.raises(DeadlineExceededError):
        await client.get("/x", deadline=4.0, raise_for_status=False)

    assert clock.monotonic() == 4.0
    assert len(mock.calls) == 1
    await client.aclose()


@pytest.mark.asyncio
async def test_no_deadline_passthrough() -> None:
    timeout = Timeout(total=7.0)
    request = _request(deadline=None, timeout=timeout)
    seen: list[Request] = []

    async def call_next(current: Request) -> Response:
        seen.append(current)
        return _response(current)

    await DeadlineMiddleware(DeadlineConfig(), clock=FakeClock())(request, call_next)

    assert seen == [request]
    assert request.extensions.timeout is timeout
    assert "x-rapidy-deadline-ms" not in request.headers


@pytest.mark.asyncio
async def test_remaining_exactly_connect_starts_attempt() -> None:
    request = _request(deadline=3.0, timeout=Timeout(connect=3.0))
    calls = 0

    async def call_next(current: Request) -> Response:
        nonlocal calls
        calls += 1
        return _response(current)

    await DeadlineMiddleware(DeadlineConfig(), clock=FakeClock())(request, call_next)

    assert calls == 1


@pytest.mark.asyncio
async def test_deadline_error_carries_context() -> None:
    request = _request(deadline=1.0, timeout=Timeout(connect=3.0))

    async def call_next(_: Request) -> Response:
        raise AssertionError("call_next must not run")

    with pytest.raises(DeadlineExceededError) as captured:
        await DeadlineMiddleware(DeadlineConfig(), clock=FakeClock())(
            request,
            call_next,
        )

    assert captured.value.upstream == "billing"
    assert captured.value.endpoint == "/x"
    assert captured.value.request_id == "request-1"
