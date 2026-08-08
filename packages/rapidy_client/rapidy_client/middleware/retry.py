from __future__ import annotations

import random
from collections.abc import Sequence
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from rapidy_client._clock import Clock
from rapidy_client._models import AttemptOutcome, CallNext, Request, Response
from rapidy_client.config import BackoffConfig, RetryConfig
from rapidy_client.errors import ConnectError, ProtocolError, ServerDisconnectedError
from rapidy_client.observability import (
    RETRY_REASON_BUDGET_EXHAUSTED,
    Observer,
    RequestContext,
    notify_observers,
    retry_reason_network,
    retry_reason_status,
)

__all__ = ("RetryMiddleware",)

_RETRYABLE_NETWORK_ERRORS: tuple[type[BaseException], ...] = (
    ConnectError,
    ServerDisconnectedError,
    ProtocolError,
)
_BUDGET_RESERVE = 10.0


class RetryMiddleware:
    """Apply retry, backoff, budget, and attempt-listener policy."""

    __slots__ = ("_budget", "_clock", "_config", "_observers", "_rng")

    def __init__(
        self,
        config: RetryConfig,
        *,
        clock: Clock,
        observers: Sequence[Observer] = (),
    ) -> None:
        self._config = config
        self._clock = clock
        self._observers = tuple(observers)
        self._rng = random.Random()
        self._budget = _BUDGET_RESERVE

    async def __call__(self, request: Request, call_next: CallNext) -> Response:
        extensions = request.extensions
        config = extensions.retry
        if config is None:
            extensions.attempt = 1
            started = self._clock.monotonic()
            response: Response | None = None
            exception: BaseException | None = None
            try:
                response = await call_next(request)
            except BaseException as exc:  # noqa: BLE001 - listeners see cancellation
                exception = exc
            outcome: AttemptOutcome = {
                "status": response.status if response is not None else None,
                "exception": exception,
                "elapsed": self._clock.monotonic() - started,
            }
            self._notify_listeners(request, outcome)
            if exception is not None:
                raise exception
            assert response is not None
            return response

        self._replenish(config)
        retryable_method = self._retryable_method(request, config)
        request_started = self._clock.monotonic()
        attempt = 0
        last_response: Response | None = None
        last_exception: BaseException | None = None

        while True:
            attempt += 1
            extensions.attempt = attempt
            attempt_started = self._clock.monotonic()
            response = None
            exception = None
            try:
                response = await call_next(request)
            except BaseException as exc:  # noqa: BLE001 - listeners see cancellation
                exception = exc

            outcome = {
                "status": response.status if response is not None else None,
                "exception": exception,
                "elapsed": self._clock.monotonic() - attempt_started,
            }
            self._notify_listeners(request, outcome)

            if exception is not None:
                if not self._is_retryable_exc(exception, config):
                    raise exception
                reason = retry_reason_network(exception)
            else:
                assert response is not None
                if response.status not in config.statuses:
                    return response
                reason = retry_reason_status(response.status)

            last_response = response
            last_exception = exception
            if (
                attempt >= config.max_attempts
                or not retryable_method
                or not request.is_replayable
            ):
                break
            if not self._has_budget(config):
                await self._dispatch_on_retry(
                    request,
                    attempt=attempt,
                    reason=RETRY_REASON_BUDGET_EXHAUSTED,
                    delay=0.0,
                    started_at=request_started,
                )
                break

            self._consume_budget()
            if response is not None:
                await response.aclose()
            delay = self._compute_delay(
                response,
                config,
                exponent=attempt - 1,
            )
            remaining = self._remaining(request)
            sleep = delay if remaining is None else min(delay, remaining)
            await self._dispatch_on_retry(
                request,
                attempt=attempt,
                reason=reason,
                delay=sleep,
                started_at=request_started,
            )
            await self._clock.sleep(sleep)

        if last_exception is not None:
            raise last_exception
        assert last_response is not None
        return last_response

    def _retryable_method(self, request: Request, config: RetryConfig) -> bool:
        return request.method.upper() in config.methods or request.extensions.idempotent

    def _is_retryable_exc(
        self,
        exc: BaseException,
        config: RetryConfig,
    ) -> bool:
        return config.on_network_errors and isinstance(
            exc,
            _RETRYABLE_NETWORK_ERRORS,
        )

    def _parse_retry_after(self, value: str) -> float | None:
        stripped = value.strip()
        if stripped.isascii() and stripped.isdigit():
            return float(int(stripped))
        try:
            parsed = parsedate_to_datetime(stripped)
        except (TypeError, ValueError, OverflowError):
            return None
        if parsed is None:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        delta = parsed.timestamp() - datetime.now(timezone.utc).timestamp()
        return delta if delta > 0 else None

    def _compute_delay(
        self,
        response: Response | None,
        config: RetryConfig,
        exponent: int,
    ) -> float:
        if response is not None and config.respect_retry_after:
            value = response.headers.get("retry-after")
            if value is not None:
                retry_after = self._parse_retry_after(value)
                if retry_after is not None:
                    return min(retry_after, config.retry_after_cap)
        return self._backoff(config.backoff, exponent)

    def _backoff(self, backoff: BackoffConfig, exponent: int) -> float:
        ceiling = min(backoff.cap, backoff.base * (2.0**exponent))
        if backoff.jitter == "full":
            return self._rng.uniform(0.0, ceiling)
        return ceiling

    def _remaining(self, request: Request) -> float | None:
        deadline = request.extensions.deadline
        if deadline is None:
            return None
        return deadline - self._clock.monotonic()

    def _replenish(self, config: RetryConfig) -> None:
        if config.budget_ratio is not None:
            self._budget = min(
                self._budget + config.budget_ratio,
                _BUDGET_RESERVE,
            )

    def _has_budget(self, config: RetryConfig) -> bool:
        return config.budget_ratio is None or self._budget >= 1.0

    def _consume_budget(self) -> None:
        self._budget -= 1.0

    def _notify_listeners(
        self,
        request: Request,
        outcome: AttemptOutcome,
    ) -> None:
        for listener in request.extensions.attempt_listeners:
            listener.on_attempt(outcome)

    async def _dispatch_on_retry(
        self,
        request: Request,
        *,
        attempt: int,
        reason: str,
        delay: float,
        started_at: float,
    ) -> None:
        extensions = request.extensions
        context = RequestContext(
            upstream=extensions.upstream,
            method=request.method,
            endpoint=extensions.endpoint,
            url=request.url,
            attempt=attempt,
            request_id=extensions.request_id,
            started_at=started_at,
            elapsed=self._clock.monotonic() - started_at,
        )
        await notify_observers(
            self._observers,
            "on_retry",
            context,
            attempt,
            reason,
            delay,
        )
