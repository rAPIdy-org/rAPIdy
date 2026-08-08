from __future__ import annotations

from rapidy.exceptions import RouteConflictError
from rapidy.routing.http.base import HTTPRouteHandler

__all__ = ('ExactPathMatcher',)


class ExactPathMatcher:
    """Temporary exact-path table replaced by UrlMatcher in milestone 03."""

    __slots__ = ('_routes',)

    def __init__(self) -> None:
        self._routes: dict[tuple[str, str], HTTPRouteHandler] = {}

    def add_route(self, route: HTTPRouteHandler) -> None:
        """Register one method/path pair or fail on a duplicate."""
        key = (route.method, route.path)
        if key in self._routes:
            msg = f'Handler already registered for {route.method} {route.path}'
            raise RouteConflictError(msg)
        self._routes[key] = route

    def resolve(self, method: str, path: str) -> HTTPRouteHandler | None:
        """Resolve an exact method/path pair."""
        return self._routes.get((method, path))
