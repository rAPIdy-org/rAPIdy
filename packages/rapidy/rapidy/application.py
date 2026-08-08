from __future__ import annotations

from collections.abc import AsyncIterator, Iterable, Iterator, MutableMapping, Sequence
from contextlib import asynccontextmanager
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
from rapidy.exceptions import HTTPException
from rapidy.lifespan import Lifespan
from rapidy.middlewares.runner import build_onion, prepare_middlewares
from rapidy.request import Request, State
from rapidy.response import Response
from rapidy.routing.http.base import raise_if_not_base_http_router
from rapidy.routing.matcher import RouteRecord, UrlMatcher
from rapidy.typedefs import ASGIScope, CallNext, LifespanCTX, LifespanHook, Middleware, Receive, Send
from rapidy.version import SERVER_INFO
from rapidy.websockets import close_unsupported_websocket

if TYPE_CHECKING:
    from rapidy.routing.http.base import BaseHTTPRouter

__all__ = ('Rapidy',)


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
        self._matcher = UrlMatcher()
        self.lifespan = Lifespan(
            self,
            lifespan_managers=[di_lifespan, _onion_lifespan, *lifespan],
            on_startup=list(on_startup),
            on_shutdown=[*on_shutdown, close_owned_di],
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
            await close_unsupported_websocket(send)
            return
        if scope_type != 'http':
            msg = f'Unsupported ASGI scope: {scope_type!r}'
            raise RuntimeError(msg)

        scope['app'] = self
        response_send = _without_head_body(send) if str(scope.get('method', '')).upper() == 'HEAD' else send

        try:
            request = Request(scope, receive)
        except HTTPException as exc:
            response = _response_from_http_exception(exc)
            await self._send_response(response, response_send)
            return
        except Exception:  # noqa: BLE001
            await self._send_response(Response('500: Internal Server Error', status=500), response_send)
            return

        if not self._onion_built:
            # Compatibility fallback for in-process transports that omit ASGI lifespan.
            self._build_onion()
        scope['_rapidy_mount_path'] = _strip_root_path(request.path, str(scope.get('root_path', '')))
        scope['_rapidy_mount_prefix'] = str(scope.get('root_path', '')).rstrip('/')

        container = self._request_di_container()
        if container is None:
            await self._handle_http(request, response_send)
            return

        async with request_di_scope(container, request):
            await self._handle_http(request, response_send)

    async def _handle_http(self, request: Request, response_send: Send) -> None:
        try:
            response = await self._run_onion(request)
        except HTTPException as exc:
            # TODO(09-exceptions-full): replace with the complete HTTPException response handler.  # noqa: FIX002
            response = _response_from_http_exception(exc)
        except Exception:  # noqa: BLE001
            response = Response('500: Internal Server Error', status=500)

        await self._send_response(response, response_send)

    async def _run_onion(self, request: Request) -> Response:
        if self._onion is None:
            msg = 'Application middleware onion has not been built'
            raise RuntimeError(msg)
        return await self._onion(request)

    async def _dispatch_terminal(self, request: Request) -> Response:
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
        return await route_match.terminal(request)

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
        onion = build_onion(prepared_middlewares, self._dispatch_terminal)
        for _prefix, subapp in self._subapps:
            subapp._build_onion()  # noqa: SLF001
        self._onion = onion
        self._onion_built = True

    async def _send_response(self, response: Response, response_send: Send) -> None:
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


def _response_from_http_exception(exc: HTTPException) -> Response:
    return Response(
        body=exc.body,
        status=exc.status_code,
        headers=exc.headers,
        content_type=exc.content_type,
    )


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
