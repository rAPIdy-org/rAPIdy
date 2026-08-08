from __future__ import annotations

import asyncio

import pytest
from rapidy_client._models import (
    URL,
    Headers,
    Request,
    RequestExtensions,
    Response,
    ResponseExtensions,
    Timeout,
)
from rapidy_client.config import RedirectConfig, RetryConfig
from rapidy_client.errors import HttpTimeoutError
from rapidy_client.middleware.retry import RetryMiddleware
from rapidy_client.middleware.timeout import TotalTimeoutMiddleware
from rapidy_client.observability import BaseObserver, RequestContext
from rapidy_client.testing import FakeClock
from rapidy_core import UNSET


def _request(*, total: float | None) -> Request:
    return Request(
        method="GET",
        url=URL("https://mock.test/x"),
        headers=Headers(),
        content=b"",
        extensions=RequestExtensions(
            upstream="test",
            endpoint="/x",
            request_id="request-1",
            timeout=Timeout(total=total),
            retry=RetryConfig(),
            idempotent=True,
            auth_override=UNSET,
            deadline=None,
            redirects=RedirectConfig(),
        ),
    )


def _response(request: Request) -> Response:
    return Response(
        status=200,
        headers=Headers(),
        request=request,
        extensions=ResponseExtensions(elapsed=0.0, attempt=1),
    )


@pytest.mark.asyncio
async def test_total_timeout_raises_phase_total() -> None:
    request = _request(total=0.01)

    async def hung(_: Request) -> Response:
        await asyncio.Event().wait()
        raise AssertionError("unreachable")

    with pytest.raises(HttpTimeoutError) as captured:
        await TotalTimeoutMiddleware()(request, hung)

    assert captured.value.phase == "total"
    assert captured.value.upstream == "test"


class _RetrySpy(BaseObserver):
    def __init__(self) -> None:
        self.retries = 0

    async def on_retry(
        self,
        ctx: RequestContext,
        attempt: int,
        reason: str,
        delay: float,
    ) -> None:
        del ctx, attempt, reason, delay
        self.retries += 1


@pytest.mark.asyncio
async def test_total_timeout_not_retried() -> None:
    request = _request(total=0.01)
    observer = _RetrySpy()
    attempts = 0

    async def hung(_: Request) -> Response:
        nonlocal attempts
        attempts += 1
        await asyncio.Event().wait()
        raise AssertionError("unreachable")

    async def timed(current: Request) -> Response:
        return await TotalTimeoutMiddleware()(current, hung)

    with pytest.raises(HttpTimeoutError) as captured:
        await RetryMiddleware(
            RetryConfig(max_attempts=3),
            clock=FakeClock(),
            observers=(observer,),
        )(request, timed)

    assert captured.value.phase == "total"
    assert attempts == 1
    assert observer.retries == 0


@pytest.mark.asyncio
async def test_total_none_has_no_wall() -> None:
    request = _request(total=None)

    async def call_next(current: Request) -> Response:
        return _response(current)

    result = await TotalTimeoutMiddleware()(request, call_next)

    assert result.status == 200


@pytest.mark.asyncio
async def test_transport_phase_timeout_is_preserved() -> None:
    request = _request(total=1.0)

    async def read_timeout(_: Request) -> Response:
        raise HttpTimeoutError("read stalled", phase="read")

    with pytest.raises(HttpTimeoutError) as captured:
        await TotalTimeoutMiddleware()(request, read_timeout)

    assert captured.value.phase == "read"
