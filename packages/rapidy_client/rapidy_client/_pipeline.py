from __future__ import annotations

from collections.abc import AsyncIterable, Sequence
from typing import Any, ClassVar, cast

from rapidy_client._content import ContentFactory
from rapidy_client._models import (
    BaseTransport,
    CallNext,
    Middleware,
    Request,
    Response,
)

_GUARD_MSG = (
    "middleware accessed request.content while is_replayable=False "
    "(a one-shot AsyncIterable). In debug mode this is forbidden by the "
    "body-access contract; use replayable bytes or ContentFactory content."
)


class _GuardedRequest:
    __slots__ = ("_raw",)

    def __init__(self, raw: Request) -> None:
        object.__setattr__(self, "_raw", raw)

    @property
    def content(self) -> bytes | AsyncIterable[bytes] | ContentFactory | None:
        raw = cast("Request", object.__getattribute__(self, "_raw"))
        if not raw.is_replayable:
            raise RuntimeError(_GUARD_MSG)
        return raw.content

    def __getattr__(self, name: str) -> Any:
        raw = cast("Request", object.__getattribute__(self, "_raw"))
        return getattr(raw, name)

    def __setattr__(self, name: str, value: Any) -> None:
        raw = cast("Request", object.__getattribute__(self, "_raw"))
        if name == "content" and not raw.is_replayable:
            raise RuntimeError(_GUARD_MSG)
        setattr(raw, name, value)


def _compose(middleware: Middleware, next_handler: CallNext) -> CallNext:
    async def handler(request: Request) -> Response:
        return await middleware(request, next_handler)

    return handler


def _transport_adapter(transport: BaseTransport) -> CallNext:
    async def handler(request: Request) -> Response:
        raw = cast("Request", getattr(request, "_raw", request))
        return await transport.handle(raw)

    return handler


class DeclaredMiddlewaresSlot:
    """Execute per-request declared middleware in writer-provided order."""

    handshake_safe: ClassVar[bool] = False

    async def __call__(self, request: Request, call_next: CallNext) -> Response:
        handler = call_next
        for middleware in reversed(request.extensions.declared_middlewares):
            handler = _compose(middleware, handler)
        return await handler(request)


def build_pipeline(
    transport: BaseTransport,
    *,
    correlation: Middleware | None = None,
    middlewares: Sequence[Middleware] = (),
    declared_slot: Middleware | None = None,
    breaker: Middleware | None = None,
    rate_limit: Middleware | None = None,
    bulkhead: Middleware | None = None,
    retry: Middleware | None = None,
    auth: Middleware | None = None,
    per_attempt_middlewares: Sequence[Middleware] = (),
    trace_context: Middleware | None = None,
    deadline: Middleware | None = None,
    redirect: Middleware | None = None,
    timeout: Middleware | None = None,
    debug: bool = False,
) -> CallNext:
    """Build the canonical middleware onion once and return its entry point."""
    declared = declared_slot if declared_slot is not None else DeclaredMiddlewaresSlot()
    ordered: list[Middleware] = []

    if correlation is not None:
        ordered.append(correlation)
    ordered.extend(middlewares)
    ordered.append(declared)
    if breaker is not None:
        ordered.append(breaker)
    if rate_limit is not None:
        ordered.append(rate_limit)
    if bulkhead is not None:
        ordered.append(bulkhead)
    if retry is not None:
        ordered.append(retry)
    if auth is not None:
        ordered.append(auth)
    ordered.extend(per_attempt_middlewares)
    if trace_context is not None:
        ordered.append(trace_context)
    if deadline is not None:
        ordered.append(deadline)
    if timeout is not None:
        ordered.append(timeout)
    if redirect is not None:
        ordered.append(redirect)

    handler = _transport_adapter(transport)
    for middleware in reversed(ordered):
        handler = _compose(middleware, handler)

    async def entry(request: Request) -> Response:
        guarded = cast("Request", _GuardedRequest(request)) if debug else request
        return await handler(guarded)

    return entry


__all__ = ("DeclaredMiddlewaresSlot", "build_pipeline")
