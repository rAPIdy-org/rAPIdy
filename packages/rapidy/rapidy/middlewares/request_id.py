from __future__ import annotations

import re
from collections.abc import AsyncIterable, AsyncIterator, Callable
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING
from uuid import uuid4

from ._utils import add_response_hook, response_headers
from rapidy.responses.streaming import StreamResponse

if TYPE_CHECKING:
    from rapidy.request import Request
    from rapidy.typedefs import CallNext, HTTPResponse

__all__ = ('RequestContext', 'RequestIDMiddleware', 'get_request_context', 'get_request_id')

_FIELD_NAME = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
_REQUEST_ID = re.compile(r'^[A-Za-z0-9._:-]+$')
_request_context: ContextVar[RequestContext | None] = ContextVar('rapidy_request_context', default=None)


@dataclass(frozen=True, slots=True)
class RequestContext:
    """Stable structured metadata for logs and downstream async calls."""

    request_id: str
    method: str
    path: str
    client: str | None


class RequestIDMiddleware:
    """Propagate or generate a safe request ID and bind structured context."""

    __slots__ = ('_generator', '_header_name', '_max_length', '_trust_incoming')

    def __init__(
        self,
        *,
        header_name: str = 'X-Request-ID',
        trust_incoming: bool = True,
        max_length: int = 128,
        generator: Callable[[], str] | None = None,
    ) -> None:
        if not _FIELD_NAME.fullmatch(header_name):
            msg = f'Invalid request ID header name: {header_name!r}'
            raise ValueError(msg)
        if max_length < 1:
            msg = 'max_length must be greater than zero'
            raise ValueError(msg)
        self._header_name = header_name
        self._trust_incoming = trust_incoming
        self._max_length = max_length
        self._generator = generator or _generate_request_id

    async def __call__(self, request: Request, call_next: CallNext) -> HTTPResponse:
        """Bind context for downstream work and annotate the final response."""
        request_id = self._incoming_request_id(request) or self._new_request_id()
        context = RequestContext(
            request_id=request_id,
            method=request.method,
            path=request.path,
            client=_client_host(request.scope.get('client')),
        )
        request.state.request_id = request_id
        request.state.request_context = context
        add_response_hook(request, lambda response: self._finalize_response(response, context))
        token = _request_context.set(context)
        try:
            return await call_next(request)
        finally:
            _request_context.reset(token)

    def _incoming_request_id(self, request: Request) -> str | None:
        if not self._trust_incoming:
            return None
        values = request.headers.getall(self._header_name, [])
        if len(values) != 1:
            return None
        return values[0] if self._valid_request_id(values[0]) else None

    def _new_request_id(self) -> str:
        request_id = self._generator()
        if not isinstance(request_id, str) or not self._valid_request_id(request_id):
            msg = 'request ID generator returned an invalid value'
            raise ValueError(msg)
        return request_id

    def _valid_request_id(self, request_id: str) -> bool:
        return len(request_id) <= self._max_length and _REQUEST_ID.fullmatch(request_id) is not None

    def _finalize_response(self, response: HTTPResponse, context: RequestContext) -> None:
        response_headers(response)[self._header_name] = context.request_id
        if isinstance(response, StreamResponse) and response._body is not None:  # noqa: SLF001
            response._body = _stream_with_context(response._body, context)  # noqa: SLF001


def get_request_context() -> RequestContext | None:
    """Return context for the current request task, if one is bound."""
    return _request_context.get()


def get_request_id() -> str | None:
    """Return the current request ID without requiring the Request object."""
    context = get_request_context()
    return context.request_id if context is not None else None


async def _stream_with_context(
    body: AsyncIterable[bytes | str],
    context: RequestContext,
) -> AsyncIterator[bytes | str]:
    token = _request_context.set(context)
    try:
        async for chunk in body:
            yield chunk
    finally:
        _request_context.reset(token)
        close = getattr(body, 'aclose', None)
        if close is not None:
            await close()


def _generate_request_id() -> str:
    return uuid4().hex


def _client_host(client: Any) -> str | None:
    if isinstance(client, (tuple, list)) and client:
        return str(client[0])
    return None
