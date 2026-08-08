from __future__ import annotations

from rapidy.routing.http.base import HTTPRouteHandler

__all__ = ('get',)


class get(HTTPRouteHandler):
    """Register a temporary exact-path GET handler."""

    def __init__(self, path: str) -> None:
        super().__init__(path=path, method='GET')
