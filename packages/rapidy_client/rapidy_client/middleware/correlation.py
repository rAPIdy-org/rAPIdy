from __future__ import annotations

from rapidy_client._models import CallNext, Headers, Request, Response

_HEADER_NAME = "X-Request-ID"


class CorrelationMiddleware:
    async def __call__(self, request: Request, call_next: CallNext) -> Response:
        request_id = request.extensions.request_id
        if not request_id:
            return await call_next(request)

        items = [
            (name, value)
            for name, value in request.headers.multi_items()
            if name.casefold() != _HEADER_NAME.casefold()
        ]
        items.append((_HEADER_NAME, request_id))
        correlated = Request(
            method=request.method,
            url=request.url,
            headers=Headers(items),
            content=request.content,
            extensions=request.extensions,
        )
        return await call_next(correlated)


__all__ = ("CorrelationMiddleware",)
