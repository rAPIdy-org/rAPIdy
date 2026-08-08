from __future__ import annotations

from collections.abc import Iterable, Iterator, MutableMapping
from typing import Any

from rapidy.helpers import ensure_response
from rapidy.lifespan import Lifespan
from rapidy.request import Request, State
from rapidy.response import Response
from rapidy.routing.http.base import HTTPRouteHandler
from rapidy.routing.matcher import ExactPathMatcher
from rapidy.typedefs import ASGIScope, LifespanCTX, LifespanHook, Receive, Send
from rapidy.version import SERVER_INFO
from rapidy.websockets import close_unsupported_websocket

__all__ = ('Rapidy',)


class Rapidy(MutableMapping[str, Any]):
    """Minimal rAPIdy 2.0 ASGI application foundation."""

    __slots__ = (
        '_matcher',
        'client_max_size',
        'lifespan',
        'server_info_in_response',
        'state',
    )

    def __init__(
        self,
        *,
        client_max_size: int = 1024**2,
        server_info_in_response: bool = False,
        lifespan: Iterable[LifespanCTX] = (),
        on_startup: Iterable[LifespanHook] = (),
        on_shutdown: Iterable[LifespanHook] = (),
        on_cleanup: Iterable[LifespanHook] = (),
        http_route_handlers: Iterable[HTTPRouteHandler] = (),
    ) -> None:
        self.client_max_size = client_max_size
        self.server_info_in_response = server_info_in_response
        self.state = State()
        self._matcher = ExactPathMatcher()
        self.lifespan = Lifespan(
            self,
            lifespan_managers=list(lifespan),
            on_startup=list(on_startup),
            on_shutdown=list(on_shutdown),
            on_cleanup=list(on_cleanup),
        )
        for route_handler in http_route_handlers:
            self.add_http_route_handler(route_handler)

    def add_http_route_handler(self, route_handler: HTTPRouteHandler) -> None:
        """Register a temporary exact-path handler."""
        self._matcher.add_route(route_handler)

    async def __call__(self, scope: ASGIScope, receive: Receive, send: Send) -> None:
        """Dispatch one ASGI connection by scope type."""
        scope_type = scope.get('type')
        if scope_type == 'lifespan':
            await self.lifespan.handle_asgi(receive, send)
            return
        if scope_type == 'websocket':
            await close_unsupported_websocket(send)
            return
        if scope_type != 'http':
            msg = f'Unsupported ASGI scope: {scope_type!r}'
            raise RuntimeError(msg)

        scope['app'] = self
        request = Request(scope, receive)
        route_handler = self._matcher.resolve(request.method, request.path)
        if route_handler is None:
            response = Response('Not Found', status=404)
        else:
            response = ensure_response(await route_handler.invoke(request))

        server_info = SERVER_INFO if self.server_info_in_response else None
        await response._send(send, server_info=server_info)  # noqa: SLF001

    def __getitem__(self, key: str) -> Any:
        return self.state[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.state[key] = value

    def __delitem__(self, key: str) -> None:
        del self.state[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.state)

    def __len__(self) -> int:
        return len(self.state)
