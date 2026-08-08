from __future__ import annotations

from collections.abc import Iterable, Iterator, MutableMapping
from typing import Any, TYPE_CHECKING

from rapidy.constants import CLIENT_MAX_SIZE
from rapidy.exceptions import HTTPException
from rapidy.lifespan import Lifespan
from rapidy.request import Request, State
from rapidy.response import Response
from rapidy.routing.http.base import raise_if_not_base_http_router
from rapidy.routing.matcher import RouteRecord, UrlMatcher
from rapidy.typedefs import ASGIScope, LifespanCTX, LifespanHook, Receive, Send
from rapidy.version import SERVER_INFO
from rapidy.websockets import close_unsupported_websocket

if TYPE_CHECKING:
    from rapidy.routing.http.base import BaseHTTPRouter

__all__ = ('Rapidy',)


class Rapidy(MutableMapping[str, Any]):
    """rAPIdy 2.0 ASGI application."""

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
        client_max_size: int = CLIENT_MAX_SIZE,
        server_info_in_response: bool = False,
        lifespan: Iterable[LifespanCTX] = (),
        on_startup: Iterable[LifespanHook] = (),
        on_shutdown: Iterable[LifespanHook] = (),
        on_cleanup: Iterable[LifespanHook] = (),
        http_route_handlers: Iterable[BaseHTTPRouter | Any] = (),
    ) -> None:
        self.client_max_size = client_max_size
        self.server_info_in_response = server_info_in_response
        self.state = State()
        self._matcher = UrlMatcher()
        self.lifespan = Lifespan(
            self,
            lifespan_managers=list(lifespan),
            on_startup=list(on_startup),
            on_shutdown=list(on_shutdown),
            on_cleanup=list(on_cleanup),
        )
        self.add_http_routers(http_route_handlers)

    @property
    def routes(self) -> tuple[RouteRecord, ...]:
        """Return the public route-registry snapshot.

        TODO(08-middleware-mounts): aggregate subapp records with their prefixes.
        """
        return self._matcher.routes

    def add_http_router(self, http_router: BaseHTTPRouter | Any) -> None:
        """Register one HTTP router object."""
        raise_if_not_base_http_router(http_router)
        http_router.route_register(application=self)

    def add_http_routers(self, route_handlers: Iterable[BaseHTTPRouter | Any]) -> None:
        """Register an iterable of HTTP router objects."""
        for route_handler in route_handlers:
            self.add_http_router(route_handler)

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
        path = _strip_root_path(request.path, str(scope.get('root_path', '')))
        response_send = _without_head_body(send) if request.method == 'HEAD' else send

        try:
            route_match = self._matcher.resolve(request.method, path)
            scope['path_params'] = route_match.path_params
            request.path_params = route_match.path_params
            response = await route_match.terminal(request)
        except HTTPException as exc:
            # TODO(09-exceptions-full): replace with the complete HTTPException response handler.  # noqa: FIX002
            response = Response(
                body=exc.body,
                status=exc.status_code,
                headers=exc.headers,
                content_type=exc.content_type,
            )
        except Exception:  # noqa: BLE001
            response = Response('500: Internal Server Error', status=500)

        server_info = SERVER_INFO if self.server_info_in_response else None
        await response._send(response_send, server_info=server_info)  # noqa: SLF001

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


def _strip_root_path(path: str, root_path: str) -> str:
    # NOTE: root_path policy is frozen in milestone 03; user documentation belongs to milestone 15.
    if root_path and path.startswith(root_path):
        return path[len(root_path) :] or '/'
    return path


def _without_head_body(send: Send) -> Send:
    async def send_without_body(message: dict[str, Any]) -> None:
        if message.get('type') == 'http.response.body':
            message = {**message, 'body': b''}
        await send(message)

    return send_without_body
