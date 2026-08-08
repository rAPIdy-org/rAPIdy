from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st
from rapidy_client import BackoffConfig, RetryConfig
from rapidy_client.middleware.retry import RetryMiddleware
from rapidy_client.testing import FakeClock


@given(
    base=st.floats(min_value=0.0, max_value=60.0, allow_nan=False),
    cap=st.floats(min_value=0.0, max_value=60.0, allow_nan=False),
    exponent=st.integers(min_value=0, max_value=64),
)
def test_full_jitter_stays_inside_exponential_ceiling(
    base: float,
    cap: float,
    exponent: int,
) -> None:
    middleware = RetryMiddleware(RetryConfig(), clock=FakeClock())
    backoff = BackoffConfig(base=base, cap=cap, jitter="full")

    delay = middleware._backoff(backoff, exponent)

    assert 0.0 <= delay <= min(cap, base * (2.0**exponent))


@given(
    base=st.floats(min_value=0.0, max_value=60.0, allow_nan=False),
    cap=st.floats(min_value=0.0, max_value=60.0, allow_nan=False),
    exponent=st.integers(min_value=0, max_value=64),
)
def test_backoff_never_exceeds_cap(
    base: float,
    cap: float,
    exponent: int,
) -> None:
    middleware = RetryMiddleware(RetryConfig(), clock=FakeClock())

    delay = middleware._backoff(
        BackoffConfig(base=base, cap=cap, jitter="full"),
        exponent,
    )

    assert delay <= cap
