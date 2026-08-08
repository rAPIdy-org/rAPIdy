from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st
from rapidy_client._models import (
    URL,
    Headers,
    Request,
    RequestExtensions,
    Response,
    ResponseExtensions,
    Timeout,
)
from rapidy_client.config import BackoffConfig, RedirectConfig, RetryConfig
from rapidy_client.middleware.retry import RetryMiddleware
from rapidy_client.testing import FakeClock
from rapidy_core import UNSET


def _response(*, retry_after: str) -> Response:
    request = Request(
        method="GET",
        url=URL("https://mock.test/x"),
        headers=Headers(),
        content=b"",
        extensions=RequestExtensions(
            upstream="test",
            endpoint="/x",
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
        headers=Headers({"Retry-After": retry_after}),
        request=request,
        extensions=ResponseExtensions(elapsed=0.0, attempt=1),
    )


@given(
    base=st.floats(min_value=0.0, max_value=10.0, allow_nan=False),
    cap=st.floats(min_value=0.0, max_value=10.0, allow_nan=False),
    exponent=st.integers(min_value=0, max_value=64),
)
def test_backoff_within_bounds(base: float, cap: float, exponent: int) -> None:
    backoff = BackoffConfig(base=base, cap=cap, jitter="full")
    middleware = RetryMiddleware(RetryConfig(), clock=FakeClock())

    delay = middleware._backoff(backoff, exponent)

    assert 0.0 <= delay <= min(cap, base * (2.0**exponent))


@given(
    base=st.floats(min_value=0.0, max_value=10.0, allow_nan=False),
    cap=st.floats(min_value=0.0, max_value=10.0, allow_nan=False),
    exponent=st.integers(min_value=0, max_value=64),
)
def test_backoff_none_jitter_is_ceiling(
    base: float,
    cap: float,
    exponent: int,
) -> None:
    backoff = BackoffConfig(base=base, cap=cap, jitter="none")
    middleware = RetryMiddleware(RetryConfig(), clock=FakeClock())

    assert middleware._backoff(backoff, exponent) == min(
        cap,
        base * (2.0**exponent),
    )


@given(seconds=st.integers(min_value=0, max_value=1_000_000))
def test_retry_after_cap_property(seconds: int) -> None:
    config = RetryConfig()
    middleware = RetryMiddleware(config, clock=FakeClock())

    delay = middleware._compute_delay(
        _response(retry_after=str(seconds)),
        config,
        exponent=0,
    )

    assert 0.0 <= delay <= config.retry_after_cap


@given(
    value=st.sampled_from(
        [
            "Thu, 01 Jan 1970 00:00:00 GMT",
            "garbage",
            "-5",
            "",
            "not-a-date",
        ]
    )
)
def test_retry_after_past_or_unparseable_falls_back(value: str) -> None:
    config = RetryConfig(backoff=BackoffConfig(jitter="none"))
    middleware = RetryMiddleware(config, clock=FakeClock())

    assert middleware._parse_retry_after(value) is None
    assert middleware._compute_delay(
        _response(retry_after=value),
        config,
        exponent=0,
    ) == min(config.backoff.cap, config.backoff.base)
