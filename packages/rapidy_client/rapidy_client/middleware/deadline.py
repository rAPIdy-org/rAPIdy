from __future__ import annotations

import dataclasses

from rapidy_client._clock import Clock
from rapidy_client._models import CallNext, Headers, Request, Response
from rapidy_client.config import DeadlineConfig
from rapidy_client.errors import DeadlineExceededError

__all__ = ("DeadlineMiddleware",)


def _replace_header(headers: Headers, name: str, value: str) -> Headers:
    folded = name.casefold()
    items = [
        (header_name, header_value)
        for header_name, header_value in headers.multi_items()
        if header_name.casefold() != folded
    ]
    items.append((name, value))
    return Headers(items)


class DeadlineMiddleware:
    """Cap an attempt by the logical deadline and propagate its remainder."""

    __slots__ = ("_clock", "_config")

    def __init__(self, config: DeadlineConfig, *, clock: Clock) -> None:
        self._config = config
        self._clock = clock

    async def __call__(self, request: Request, call_next: CallNext) -> Response:
        extensions = request.extensions
        if extensions.deadline is None:
            return await call_next(request)

        remaining = extensions.deadline - self._clock.monotonic()
        connect = extensions.timeout.connect
        if remaining < connect:
            raise DeadlineExceededError(
                "deadline budget exhausted before attempt "
                f"(remaining={remaining:.6f}s < connect={connect:.6f}s)",
                upstream=extensions.upstream,
                endpoint=extensions.endpoint,
                request_id=extensions.request_id,
            )

        current_total = extensions.timeout.total
        capped_total = (
            remaining if current_total is None else min(current_total, remaining)
        )
        extensions.timeout = dataclasses.replace(
            extensions.timeout,
            total=capped_total,
        )
        if self._config.propagate:
            milliseconds = max(0, int(remaining * 1000))
            request.headers = _replace_header(
                request.headers,
                self._config.header,
                str(milliseconds),
            )
        return await call_next(request)
