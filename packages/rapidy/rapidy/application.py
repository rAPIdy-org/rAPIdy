from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Iterable, Iterator, MutableMapping, Sequence
from contextlib import asynccontextmanager, suppress
from typing import Any, cast, TYPE_CHECKING

from rapidy.constants import CLIENT_MAX_SIZE
from rapidy.depends import AsyncContainer, BaseScope, Provider, Scope, ValidationSettings
from rapidy.di import (
    close_owned_di,
    DEFAULT_DI_LOCK_FACTORY,
    DEFAULT_DI_VALIDATION_SETTINGS,
    di_lifespan,
    DIConfig,
    LockFactory,
    request_di_scope,
)
from rapidy.exceptions import HTTPException, HTTPNotFound
from rapidy.lifespan import Lifespan
from rapidy.middlewares.runner import build_onion, prepare_middlewares
from rapidy.request import Request, State
from rapidy.response import Response
from rapidy.responses.streaming import StreamResponse
from rapidy.routing.http.base import raise_if_not_base_http_router
from rapidy.routing.matcher import RouteMatch, RouteRecord, UrlMatcher
from rapidy.typedefs import ASGIScope, CallNext, Handler, LifespanCTX, LifespanHook, Middleware, Receive, Send
from rapidy.version import SERVER_INFO
from rapidy.websockets import WebSocket, WebSocketDisconnect, WebSocketState

if TYPE_CHECKING:
    from rapidy.routing.http.base import BaseHTTPRouter

__all__ = ('Rapidy',)

logger = logging.getLogger('rapidy.application')


class Rapidy(MutableMapping[str, Any]):
    """rAPIdy 2.0 ASGI application."""

    __slots__ = (
        '_client_max_size',
        '_di_config',
        '_di_container_closed',
        '_di_container_owned',
        '_matcher',
        '_middlewares',
        '_onion',
        '_onion_built',
        '_root_app',
        'lifespan',
        'server_info_in_response',
        'state',
    )

    def __init__(
        self,
        *,
        client_max_size: int = CLIENT_MAX_SIZE,
        server_info_in_response: bool = False,
        middlewares: Iterable[Middleware] | None = None,
        lifespan: Iterable[LifespanCTX] = (),
        on_startup: Iterable[LifespanHook] = (),
        on_shutdown: Iterable[LifespanHook] = (),
        on_cleanup: Iterable[LifespanHook] = (),
        http_route_handlers: Iterable[BaseHTTPRouter | Any] = (),
        di_container: AsyncContainer | None = None,
        di_providers: Sequence[Provider] = (),
        di_scopes: type[BaseScope] = Scope,
        di_context: dict[Any, Any] | None = None,
        di_lock_factory: LockFactory | None = DEFAULT_DI_LOCK_FACTORY,
        di_skip_validation: bool = False,
        di_start_scope: BaseScope | None = None,
        di_validation_settings: ValidationSettings = DEFAULT_DI_VALIDATION_SETTINGS,
    ) -> None:
        self._client_max_size = client_max_size
        self._root_app: Rapidy | None = None
        self._di_container_closed = False
        self._di_container_owned = False
        self._middlewares = list(middlewares or ())
        self._onion: CallNext | None = None
        self._onion_built = False
        self._di_config = DIConfig(
            container=di_container,
            providers=tuple(di_providers),
            scopes=di_scopes,
            context=di_context,
            lock_factory=di_lock_factory,
            skip_validation=di_skip_validation,
            start_scope=di_start_scope,
            validation_settings=di_validation_settings,
        )
        self.server_info_in_response = server_info_in_response
        self.state = State()
        self.state['_open_websockets'] = set()
        self._matcher = UrlMatcher()
        self.lifespan = Lifespan(
            self,
            lifespan_managers=[di_lifespan, _onion_lifespan, *lifespan],
            on_startup=list(on_startup),
            on_shutdown=[self._close_open_websockets, *on_shutdown, close_owned_di],
            on_cleanup=list(on_cleanup),
        )
        self.add_http_routers(http_route_handlers)

    @property
    def client_max_size(self) -> int:
        """Return the per-application request-body limit."""
        return self._client_max_size

    @property
    def routes(self) -> tuple[RouteRecord, ...]:
        """Return root and recursively mounted route records with full paths."""
        records = list(self._matcher.routes)
        for prefix, subapp in self._subapps:
            records.extend(record._replace(path=f'{prefix}{record.path}') for record in subapp.routes)
        return tuple(records)

    @property
    def di_container(self) -> AsyncContainer | None:
        """Return the active root container, or ``None`` outside root startup."""
        if self._root_app is not None:
            return None
        return self.state.get('di_container')

    def _bind_to_root(self, root_app: Rapidy) -> None:
        """Mark this application as a mounted child of the given root."""
        self._root_app = root_app._root_app or root_app
        for _prefix, subapp in self._subapps:
            subapp._bind_to_root(self._root_app)  # noqa: SLF001

    def _request_di_container(self) -> AsyncContainer | None:
        if self._root_app is not None:
            return self._root_app.di_container
        return self.di_container

    def add_http_router(self, http_router: BaseHTTPRouter | Any) -> None:
        """Register one HTTP router object."""
        if self._onion_built:
            msg = 'Cannot add HTTP route after application startup'
            raise RuntimeError(msg)
        raise_if_not_base_http_router(http_router)
        http_router.route_register(application=self)

    def add_http_routers(self, route_handlers: Iterable[BaseHTTPRouter | Any]) -> None:
        """Register an iterable of HTTP router objects."""
        for route_handler in route_handlers:
            self.add_http_router(route_handler)

    def add_subapp(self, prefix: str, subapp: Rapidy) -> Rapidy:
        """Mount a child application under one normalized URL prefix."""
        if not prefix.startswith('/'):
            msg = "prefix must start with '/'"
            raise ValueError(msg)
        if prefix == '/':
            msg = "prefix cannot be '/'"
            raise ValueError(msg)
        if prefix.endswith('/'):
            msg = "prefix must not end with '/'"
            raise ValueError(msg)
        if self._onion_built:
            msg = 'Cannot add sub application after application startup'
            raise RuntimeError(msg)
        if subapp is self:
            msg = 'Application cannot mount itself'
            raise ValueError(msg)

        subapp._bind_to_root(self)
        self._matcher.add_prefix(prefix, subapp)
        self.lifespan.append(_subapp_lifespan(subapp))
        return subapp

    async def __call__(self, scope: ASGIScope, receive: Receive, send: Send) -> None:
        """Dispatch one ASGI connection by scope type."""
        scope_type = scope.get('type')
        if scope_type == 'lifespan':
            await self.lifespan.handle_asgi(receive, send)
            return
        if scope_type == 'websocket':
            await self._handle_websocket(scope, receive, send)
            return
        if scope_type != 'http':
            msg = f'Unsupported ASGI scope: {scope_type!r}'
            raise RuntimeError(msg)

        scope['app'] = self
        response_send = _without_head_body(send) if str(scope.get('method', '')).upper() == 'HEAD' else send
        tracking_send = _TrackingSend(response_send)

        try:
            request = Request(scope, receive)
        except HTTPException as exc:
            await self._send_response(_exception_response(exc), tracking_send)
            return
        except Exception:
            logger.exception('Unhandled exception while initializing request')
            await self._send_response(_internal_server_error_response(), tracking_send)
            return
        request._asgi_send = tracking_send  # noqa: SLF001
        request._asgi_receive = receive  # noqa: SLF001

        if not self._onion_built:
            # Compatibility fallback for in-process transports that omit ASGI lifespan.
            self._build_onion()
        scope['_rapidy_mount_path'] = _strip_root_path(request.path, str(scope.get('root_path', '')))
        scope['_rapidy_mount_prefix'] = str(scope.get('root_path', '')).rstrip('/')

        container = self._request_di_container()
        if container is None:
            await self._handle_http(request, tracking_send)
            return

        async with request_di_scope(container, request):
            await self._handle_http(request, tracking_send)

    async def _handle_websocket(self, scope: ASGIScope, receive: Receive, send: Send) -> None:
        if not self._onion_built:
            await receive()
            await send(
                {
                    'type': 'websocket.close',
                    'code': 1011,
                    'reason': 'Application startup has not completed',
                }
            )
            return

        path = _strip_root_path(str(scope.get('path', '')), str(scope.get('root_path', '')))
        resolved = self._resolve_ws_target(path)
        if resolved is None:
            await receive()
            await send({'type': 'websocket.close', 'code': 1000})
            return

        matched_app, route_match = resolved
        request_scope = dict(scope)
        request_scope.update(
            {
                'app': matched_app,
                'method': 'GET',
                'path_params': route_match.path_params,
            }
        )
        ws = WebSocket(scope, receive, send)
        ws.path_params = route_match.path_params

        try:
            request = Request(request_scope, receive)
        except HTTPException:
            await ws.close(code=1000)
            return
        except Exception:
            logger.exception('Unhandled exception while initializing WebSocket request')
            await ws.close(code=1011)
            return
        request.path_params = route_match.path_params

        root_container = self._request_di_container()
        if root_container is None:
            await ws.close(code=1011, reason='Application dependency container is not available')
            return

        open_websockets = cast('set[WebSocket]', self.state['_open_websockets'])
        open_websockets.add(ws)
        try:
            async with root_container(
                context={WebSocket: ws, Request: request},
                scope=Scope.SESSION,
            ) as session_container:
                request.state.di_container = session_container
                try:
                    ws_terminal = cast('Handler', route_match.terminal)
                    await ws_terminal(ws, request)
                except WebSocketDisconnect:
                    pass
                except HTTPException:
                    code = 1000 if ws.client_state is WebSocketState.CONNECTING else 1011
                    await ws.close(code=code)
                except Exception:
                    logger.exception('Unhandled exception during WebSocket processing')
                    await ws.close(code=1011)
                else:
                    await ws.close(code=1000)
        finally:
            open_websockets.discard(ws)

    async def _close_open_websockets(self) -> None:
        """Close accepted WebSockets before user shutdown and cleanup hooks."""
        open_websockets = cast('set[WebSocket]', self.state['_open_websockets'])
        for ws in tuple(open_websockets):
            # Registration precedes the user-owned accept call, so only connected sockets close here.
            if ws.application_state is not WebSocketState.CONNECTED:
                continue
            try:
                await ws.close(code=1001)
            except Exception:
                logger.exception('Error while closing WebSocket connection on shutdown')

    def _resolve_ws_target(self, path: str) -> tuple[Rapidy, RouteMatch] | None:
        for prefix, subapp in self._subapps:
            if path == prefix or path.startswith(f'{prefix}/'):
                return subapp._resolve_ws_target(path[len(prefix) :] or '/')  # noqa: SLF001
        try:
            return self, self._matcher.resolve_ws(path)
        except HTTPNotFound:
            return None

    async def _handle_http(self, request: Request, tracking_send: _TrackingSend) -> None:
        try:
            response = await self._run_onion(request)
            await self._send_response(response, tracking_send, app=request.app, request=request)
        except ConnectionResetError:
            logger.debug('Client disconnected while reading request body: %s %s', request.method, request.path)
        except HTTPException as exc:
            if tracking_send.started:
                logger.exception('HTTP exception raised after response was started')
                await _finalize_started_response(tracking_send)
            else:
                await self._send_response(_exception_response(exc), tracking_send, app=request.app)
        except Exception:
            logger.exception('Unhandled exception during request processing')
            if tracking_send.started:
                await _finalize_started_response(tracking_send)
            else:
                await self._send_response(_internal_server_error_response(), tracking_send, app=request.app)

    async def _run_onion(self, request: Request) -> Response | StreamResponse:
        if self._onion is None:
            msg = 'Application middleware onion has not been built'
            raise RuntimeError(msg)
        return cast('Response | StreamResponse', await self._onion(request))

    async def _dispatch_terminal(self, request: Request) -> Response | StreamResponse:
        path = str(request.scope['_rapidy_mount_path'])
        for prefix, subapp in self._subapps:
            if path == prefix or path.startswith(f'{prefix}/'):
                request.app = subapp
                request.scope['app'] = subapp
                request.scope['_rapidy_mount_path'] = path[len(prefix) :] or '/'
                current_prefix = str(request.scope.get('_rapidy_mount_prefix', ''))
                request.scope['_rapidy_mount_prefix'] = f'{current_prefix}{prefix}'
                # Request.client_max_size reads request.app lazily, after this rebind.
                return await subapp._run_onion(request)  # noqa: SLF001

        route_match = self._matcher.resolve(request.method, path)
        request.scope['path_params'] = route_match.path_params
        request.path_params = route_match.path_params
        return cast('Response | StreamResponse', await route_match.terminal(request))

    def _can_resolve(self, method: str, path: str) -> bool:
        for prefix, subapp in self._subapps:
            if path == prefix or path.startswith(f'{prefix}/'):
                return subapp._can_resolve(method, path[len(prefix) :] or '/')  # noqa: SLF001
        try:
            self._matcher.resolve(method, path)
        except HTTPException:
            return False
        return True

    @property
    def _subapps(self) -> tuple[tuple[str, Rapidy], ...]:
        return cast('tuple[tuple[str, Rapidy], ...]', tuple(self._matcher._prefixes))  # noqa: SLF001

    def _build_onion(self) -> None:
        if self._onion_built:
            return
        prepared_middlewares = prepare_middlewares(self._middlewares)
        onion = build_onion(prepared_middlewares, cast('CallNext', self._dispatch_terminal))
        for _prefix, subapp in self._subapps:
            subapp._build_onion()  # noqa: SLF001
        self._onion = onion
        self._onion_built = True

    async def _send_response(
        self,
        response: Response | StreamResponse,
        response_send: Send,
        *,
        app: Rapidy | None = None,
        request: Request | None = None,
    ) -> None:
        response_app = app if app is not None else self
        server_info = SERVER_INFO if response_app.server_info_in_response else None
        if isinstance(response, StreamResponse):
            if request is None:
                msg = 'Streaming responses require the active Request transport'
                raise RuntimeError(msg)
            await response.prepare(request)
            await response._send_stream(  # noqa: SLF001
                response_send,
                request._asgi_receive,  # noqa: SLF001
                server_info=server_info,
            )
            return
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


class _TrackingSend:
    __slots__ = ('_send', 'completed', 'started')

    def __init__(self, send: Send) -> None:
        self._send = send
        self.started = False
        self.completed = False

    async def __call__(self, message: dict[str, Any]) -> None:
        message_type = message.get('type')
        if message_type == 'http.response.start':
            self.started = True
        elif message_type == 'http.response.body' and not message.get('more_body', False):
            self.completed = True
        await self._send(message)


def _exception_response(exc: HTTPException) -> Response:
    content_type = exc.content_type
    if content_type is None and exc.text is not None:
        content_type = 'text/plain'
    if exc.body is not None:
        return Response(
            body=exc.body,
            status=exc.status_code,
            headers=exc.headers,
            content_type=content_type,
            reason=exc.reason,
        )
    return Response(
        status=exc.status_code,
        headers=exc.headers,
        text=exc.text,
        content_type=content_type,
        reason=exc.reason,
    )


def _internal_server_error_response() -> Response:
    return Response(
        status=500,
        text='500: Internal Server Error',
        content_type='text/plain',
    )


async def _finalize_started_response(tracking_send: _TrackingSend) -> None:
    if tracking_send.completed:
        return
    with suppress(Exception):
        await tracking_send({'type': 'http.response.body', 'body': b'', 'more_body': False})


def _without_head_body(send: Send) -> Send:
    async def send_without_body(message: dict[str, Any]) -> None:
        if message.get('type') == 'http.response.body':
            message = {**message, 'body': b''}
        await send(message)

    return send_without_body


@asynccontextmanager
async def _onion_lifespan(app: Rapidy) -> AsyncIterator[None]:
    if app._root_app is None:  # noqa: SLF001
        app._build_onion()  # noqa: SLF001
    yield


def _subapp_lifespan(subapp: Rapidy) -> LifespanCTX:
    @asynccontextmanager
    async def lifespan_context(_parent: Rapidy) -> AsyncIterator[None]:
        async with subapp.lifespan.ctx_manager():
            yield

    return lifespan_context
