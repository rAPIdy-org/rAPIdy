from __future__ import annotations

import asyncio

from rapidy_client._models import CallNext, Request, Response
from rapidy_client.errors import HttpTimeoutError

__all__ = ("TotalTimeoutMiddleware",)


class TotalTimeoutMiddleware:
    """Enforce ``Timeout.total`` around all redirect hops in one attempt."""

    __slots__ = ()

    async def __call__(self, request: Request, call_next: CallNext) -> Response:
        extensions = request.extensions
        total = extensions.timeout.total
        if total is None:
            return await call_next(request)
        try:
            async with asyncio.timeout(total):
                return await call_next(request)
        except HttpTimeoutError:
            raise
        except TimeoutError as exc:
            raise HttpTimeoutError(
                phase="total",
                upstream=extensions.upstream,
                endpoint=extensions.endpoint,
                request_id=extensions.request_id,
            ) from exc
