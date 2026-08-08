from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st
from rapidy_client import (
    UNSET,
    URL,
    BackoffConfig,
    Headers,
    RedirectConfig,
    Request,
    RequestExtensions,
    Response,
    ResponseExtensions,
    RetryConfig,
    Timeout,
)
from rapidy_client.middleware.retry import RetryMiddleware
from rapidy_client.testing import FakeClock


def _response(value: str) -> Response:
    request = Request(
        method="GET",
        url=URL("https://mock.test/retry"),
        headers=Headers(),
        content=None,
        extensions=RequestExtensions(
            upstream="property",
            endpoint="/retry",
            request_id=None,
            timeout=Timeout(),
            retry=RetryConfig(),
            idempotent=True,
            auth_override=UNSET,
            deadline=None,
            redirects=RedirectConfig(),
        ),
    )
    return Response(
        status=503,
        headers=Headers({"retry-after": value}),
        request=request,
        extensions=ResponseExtensions(elapsed=0.0, attempt=1),
    )


@given(seconds=st.integers(min_value=0, max_value=1_000_000))
def test_retry_after_delta_seconds_is_capped(seconds: int) -> None:
    config = RetryConfig(retry_after_cap=30.0)
    middleware = RetryMiddleware(config, clock=FakeClock())

    delay = middleware._compute_delay(_response(str(seconds)), config, exponent=0)

    assert delay == min(float(seconds), config.retry_after_cap)


@given(value=st.sampled_from(["", "-1", "garbage", "Thu, 01 Jan 1970 00:00:00 GMT"]))
def test_invalid_or_past_retry_after_falls_back_to_backoff(value: str) -> None:
    config = RetryConfig(backoff=BackoffConfig(base=0.25, cap=1.0, jitter="none"))
    middleware = RetryMiddleware(config, clock=FakeClock())

    assert middleware._compute_delay(_response(value), config, exponent=0) == 0.25
