from __future__ import annotations

import inspect
from typing import Any

from rapidy.request import Request
from rapidy.typedefs import Handler

__all__ = ('BaseHTTPRouter', 'HTTPRouteHandler')


class BaseHTTPRouter:
    """Minimal common route object retained for decorator compatibility."""

    __slots__ = ('path',)

    def __init__(self, path: str) -> None:
        self.path = path


class HTTPRouteHandler(BaseHTTPRouter):
    """Temporary exact-path HTTP handler used until milestone 03."""

    __slots__ = ('_handler', 'method')

    def __init__(self, path: str, method: str) -> None:
        super().__init__(path)
        self.method = method
        self._handler: Handler | None = None

    def __call__(self, handler: Handler) -> HTTPRouteHandler:
        """Bind the decorated callable and return the route object."""
        self._handler = handler
        return self

    @property
    def handler(self) -> Handler:
        """Return the bound terminal callable."""
        if self._handler is None:
            msg = f'No callable registered for {self.method} {self.path}'
            raise RuntimeError(msg)
        return self._handler

    async def invoke(self, request: Request) -> Any:
        """Invoke a zero-argument or single-Request terminal."""
        parameters = inspect.signature(self.handler).parameters
        if not parameters:
            return await self.handler()
        if len(parameters) == 1:
            return await self.handler(request)
        msg = 'Milestone 02 handlers accept zero arguments or one Request argument'
        raise TypeError(msg)
