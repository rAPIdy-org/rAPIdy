from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Iterable, Iterator, Mapping, MutableMapping, Sequence
from contextlib import asynccontextmanager, suppress
from dataclasses import replace
from inspect import isawaitable
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
from rapidy.middlewares._utils import apply_response_hooks
from rapidy.middlewares.runner import build_onion, prepare_middlewares
from rapidy.openapi import create_openapi_schema, OpenAPIConfig, OpenAPIRenderPlugin
from rapidy.problems import ExceptionHandler
from rapidy.request import Request, State
from rapidy.response import Response
from rapidy.responses.streaming import StreamResponse
from rapidy.routing.http.base import raise_if_not_base_http_router
from rapidy.routing.http.routers import get
from rapidy.routing.matcher import RouteMatch, RouteRecord, UrlMatcher
from rapidy.routing.reverse import (
    DuplicateRouteNameError,
    InvalidPathParameterError,
    render_path_template,
    RouteNotFoundError,
    URLPath,
)
from rapidy.security import Guard, SecurityConfig, SecurityScheme
from rapidy.security.runtime import authorize_request
from rapidy.typedefs import ASGIScope, CallNext, Handler, LifespanCTX, LifespanHook, Middleware, Receive, Send, Unset
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
        '_exception_handlers',
        '_matcher',
        '_middlewares',
        '_onion',
        '_onion_built',
        '_openapi_config',
        '_openapi_schema',
        '_parent_app',
        '_root_app',
        '_security_config',
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
        openapi_config: OpenAPIConfig | None = None,
        security: SecurityConfig | None = None,
        exception_handlers: Mapping[type[Exception], ExceptionHandler] | None = None,
    ) -> None:
        self._client_max_size = client_max_size
        self._parent_app: Rapidy | None = None
        self._root_app: Rapidy | None = None
        self._di_container_closed = False
        self._di_container_owned = False
        self._middlewares = list(middlewares or ())
        self._onion: CallNext | None = None
        self._onion_built = False
        self._security_config = security
        self._exception_handlers: dict[type[Exception], ExceptionHandler] = {}
        for exception_type, handler in (exception_handlers or {}).items():
            self.add_exception_handler(exception_type, handler)
        self._openapi_config = _bind_openapi_security(openapi_config, security)
        self._openapi_schema: dict[str, Any] | None = None
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
        if self._openapi_config is not None:
            self._add_openapi_routes()

    @property
    def client_max_size(self) -> int:
        """Return the per-application request-body limit."""
        return self._client_max_size

    @property
    def routes(self) -> tuple[RouteRecord, ...]:
        """Return root and recursively mounted route records with full paths."""
        document_requirements = tuple(self._openapi_config.security) if self._openapi_config is not None else ()
        return self._openapi_routes(
            inherited_security=None,
            document_requirements=document_requirements,
            prefix='',
        )

    @property
    def openapi_config(self) -> OpenAPIConfig | None:
        """Return the active OpenAPI configuration, or ``None`` when schema routes are disabled."""
        return self._openapi_config

    @property
    def openapi_schema(self) -> dict[str, Any] | None:
        """Build and cache this application's OpenAPI schema on first access."""
        if self._openapi_config is None:
            return None
        if self._openapi_schema is None:
            self._openapi_schema = create_openapi_schema(self.routes, self._openapi_generation_config())
        return self._openapi_schema

    def url_for(self, name: str, **path_params: object) -> URLPath:
        """Build an application-relative URL for one explicitly named route."""
        records = [record for record in self.routes if record.route_kwargs.get('name') == name]
        if not records:
            raise RouteNotFoundError(name=name)
        templates = {record.path for record in records}
        if len(templates) != 1:
            raise DuplicateRouteNameError(name=name)
        template = templates.pop()
        path = render_path_template(template, path_params, route_name=name)
        if not any(self._can_resolve(record.method, path) for record in records):
            raise InvalidPathParameterError(name=name)
        return path

    def static_url(self, name: str, path: str) -> URLPath:
        """Build a URL for a named :class:`StaticFiles` tree."""
        return self.url_for(name, path=path)

    def route_template(self, path: str, *, method: str = 'GET', websocket: bool = False) -> str | None:
        """Resolve a low-cardinality route template without exposing path values."""
        _ = method  # Retained in the public API so callers can describe the attempted operation.
        for prefix, subapp in self._subapps:
            if path == prefix or path.startswith(f'{prefix}/'):
                child_template = subapp.route_template(
                    path[len(prefix) :] or '/',
                    method=method,
                    websocket=websocket,
                )
                return None if child_template is None else f'{prefix}{child_template}'
        return self._matcher.route_template(path, websocket=websocket)

    @property
    def di_container(self) -> AsyncContainer | None:
        """Return the active root container, or ``None`` outside root startup."""
        if self._root_app is not None:
            return None
        return self.state.get('di_container')

    def _bind_to_root(self, parent_app: Rapidy) -> None:
        """Mark this application as a mounted child of the given parent and root."""
        self._parent_app = parent_app
        self._root_app = parent_app._root_app or parent_app
        for _prefix, subapp in self._subapps:
            subapp._bind_to_root(self)  # noqa: SLF001

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
        self._invalidate_openapi_schema()

    def add_http_routers(self, route_handlers: Iterable[BaseHTTPRouter | Any]) -> None:
        """Register an iterable of HTTP router objects."""
        for route_handler in route_handlers:
            self.add_http_router(route_handler)

    def add_exception_handler(
        self,
        exception_type: type[Exception],
        handler: ExceptionHandler,
    ) -> None:
        """Register an application-local exception handler before startup."""
        if self._onion_built:
            msg = 'Cannot add exception handler after application startup'
            raise RuntimeError(msg)
        if not isinstance(exception_type, type) or not issubclass(exception_type, Exception):
            msg = 'Exception handler key must be an Exception subclass'
            raise TypeError(msg)
        if not callable(handler):
            msg = 'Exception handler must be callable'
            raise TypeError(msg)
        self._exception_handlers[exception_type] = handler

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
        self._invalidate_openapi_schema()
        return subapp

    def _invalidate_openapi_schema(self) -> None:
        self._openapi_schema = None
        if self._root_app is not None:
            self._root_app._openapi_schema = None  # noqa: SLF001

    def _add_openapi_routes(self) -> None:
        config = cast('OpenAPIConfig', self._openapi_config)

        async def openapi_json() -> dict[str, Any]:
            return cast('dict[str, Any]', self.openapi_schema)

        self.add_http_router(
            get(
                config.json_path,
                include_in_schema=False,
                public=True,
                response_content_type='application/json',
                response_type=dict[str, Any],
            )(openapi_json)
        )

        def create_ui_handler(plugin: OpenAPIRenderPlugin) -> Handler:
            async def openapi_ui(request: Request) -> Response:
                prefix = str(request.scope.get('_rapidy_mount_prefix', ''))
                schema = cast('dict[str, Any]', self.openapi_schema)
                document = plugin.render(
                    request,
                    schema,
                    schema_url=f'{prefix}{config.json_path}',
                )
                return Response(document, content_type=plugin.media_type)

            return openapi_ui

        for plugin in config.get_render_plugins():
            self.add_http_router(get(plugin.path, include_in_schema=False, public=True)(create_ui_handler(plugin)))

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
        except Exception as exc:
            _raise_server_exception_for_tests(scope, exc)
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

    async def _handle_websocket(  # noqa: C901, PLR0915
        self,
        scope: ASGIScope,
        receive: Receive,
        send: Send,
    ) -> None:
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
        route_template = self.route_template(path, websocket=True)
        if route_template is not None:
            scope['_rapidy_route_template'] = route_template
        resolved = self._resolve_ws_target(path)
        if resolved is None:
            await receive()
            await send({'type': 'websocket.close', 'code': 1000})
            return

        matched_app, route_match = resolved
        request_scope = dict(scope)
        shared_state = cast('dict[str, Any]', scope.setdefault('state', {}))
        request_scope.update(
            {
                'app': matched_app,
                'method': 'GET',
                'path_params': route_match.path_params,
                'state': shared_state,
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
                    try:
                        await matched_app._authorize_route(request, route_match.route_kwargs)  # noqa: SLF001
                    except HTTPException as exc:
                        await ws.close(code=1008, reason=exc.reason)
                        return
                    ws_terminal = cast('Handler', route_match.terminal)
                    await ws_terminal(ws, request)
                except WebSocketDisconnect:
                    pass
                except HTTPException:
                    code = 1000 if ws.client_state is WebSocketState.CONNECTING else 1011
                    await ws.close(code=code)
                except Exception as exc:
                    _raise_server_exception_for_tests(scope, exc)
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
            response = await apply_response_hooks(request, response)
            await self._send_response(response, tracking_send, app=request.app, request=request)
        except ConnectionResetError:
            logger.debug('Client disconnected while reading request body: %s %s', request.method, request.path)
        except HTTPException as exc:
            if tracking_send.started:
                logger.exception('HTTP exception raised after response was started')
                await _finalize_started_response(tracking_send)
            else:
                exception_response = await self._registered_exception_response(request, exc)
                if exception_response is None:
                    exception_response = _exception_response(exc)
                exception_response = await apply_response_hooks(request, exception_response)
                await self._send_response(exception_response, tracking_send, app=request.app, request=request)
        except Exception as exc:
            if tracking_send.started:
                logger.exception('Unhandled exception after response was started')
                await _finalize_started_response(tracking_send)
            else:
                exception_response = await self._registered_exception_response(request, exc)
                if exception_response is None:
                    logger.exception('Unhandled exception during request processing')
                    _raise_server_exception_for_tests(request.scope, exc)
                    exception_response = _internal_server_error_response()
                exception_response = await apply_response_hooks(request, exception_response)
                await self._send_response(exception_response, tracking_send, app=request.app, request=request)

    async def _registered_exception_response(
        self,
        request: Request,
        exception: Exception,
    ) -> Response | StreamResponse | None:
        handler = self._find_exception_handler(request.app, exception)
        if handler is None:
            return None
        try:
            response = handler(request, exception)
            if isawaitable(response):
                response = await response
        except Exception as handler_exception:
            _raise_server_exception_for_tests(request.scope, handler_exception)
            logger.exception('Unhandled exception in application exception handler')
            return _internal_server_error_response()
        if not isinstance(response, (Response, StreamResponse)):
            msg = 'Exception handlers must return a Response or StreamResponse'
            type_error = TypeError(msg)
            _raise_server_exception_for_tests(request.scope, type_error)
            logger.error(msg)
            return _internal_server_error_response()
        return response

    @staticmethod
    def _find_exception_handler(app: Rapidy, exception: Exception) -> ExceptionHandler | None:
        exception_type = type(exception)
        mro = exception_type.mro()
        for candidate_app in reversed(app._application_chain):
            matches = [
                (mro.index(registered) if registered in mro else len(mro), handler)
                for registered, handler in candidate_app._exception_handlers.items()  # noqa: SLF001
                if isinstance(exception, registered)
            ]
            if matches:
                return min(matches, key=lambda item: item[0])[1]
        return None

    async def _run_onion(self, request: Request) -> Response | StreamResponse:
        if self._onion is None:
            msg = 'Application middleware onion has not been built'
            raise RuntimeError(msg)
        return await self._onion(request)

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

        local_template = self._matcher.route_template(path)
        mount_prefix = str(request.scope.get('_rapidy_mount_prefix', ''))
        if local_template is not None:
            request.scope['_rapidy_route_template'] = f'{mount_prefix}{local_template}'
        route_match = self._matcher.resolve(request.method, path)
        request.scope['path_params'] = route_match.path_params
        request.path_params = route_match.path_params
        await self._authorize_route(request, route_match.route_kwargs)
        return await route_match.terminal(request)

    async def _authorize_route(self, request: Request, route_kwargs: dict[str, Any]) -> None:
        configs = [
            app._security_config  # noqa: SLF001
            for app in self._application_chain
            if app._security_config is not None  # noqa: SLF001
        ]
        schemes: dict[str, SecurityScheme] = {}
        guards: list[Guard] = []
        for config in configs:
            for scheme in config.schemes:
                existing = schemes.get(scheme.name)
                if existing is not None and existing.openapi_schema != scheme.openapi_schema:
                    msg = f'Conflicting runtime security scheme: {scheme.name!r}'
                    raise RuntimeError(msg)
                schemes[scheme.name] = scheme
            guards.extend(config.guards)

        public = route_kwargs.get('public') is True
        configured_guards = route_kwargs.get('guards', Unset)
        if configured_guards is not Unset:
            guards.extend(configured_guards)
        requirements: Any
        if public:
            requirements = ()
            guards = []
        elif configs:
            configured_requirements = route_kwargs.get('security', Unset)
            requirements = configs[-1].requirements if configured_requirements is Unset else configured_requirements
        else:
            # Keep pre-milestone OpenAPI-only metadata non-enforcing until a SecurityConfig is installed.
            requirements = ()

        await authorize_request(
            request,
            schemes=schemes,
            requirements=requirements,
            guards=guards,
        )

    @property
    def _application_chain(self) -> tuple[Rapidy, ...]:
        chain: list[Rapidy] = []
        current: Rapidy | None = self
        while current is not None:
            chain.append(current)
            current = current._parent_app  # noqa: SLF001
        chain.reverse()
        return tuple(chain)

    def _openapi_routes(
        self,
        *,
        inherited_security: SecurityConfig | None,
        document_requirements: tuple[Any, ...],
        prefix: str,
    ) -> tuple[RouteRecord, ...]:
        effective_security = self._security_config or inherited_security
        records: list[RouteRecord] = []
        for record in self._matcher.routes:
            route_kwargs = dict(record.route_kwargs)
            configured = route_kwargs.get('security', Unset)
            if (
                configured is Unset
                and effective_security is not None
                and tuple(effective_security.requirements) != document_requirements
            ):
                route_kwargs['security'] = effective_security.requirements
            records.append(record._replace(path=f'{prefix}{record.path}', route_kwargs=route_kwargs))
        for child_prefix, subapp in self._subapps:
            records.extend(
                subapp._openapi_routes(  # noqa: SLF001
                    inherited_security=effective_security,
                    document_requirements=document_requirements,
                    prefix=f'{prefix}{child_prefix}',
                )
            )
        return tuple(records)

    def _openapi_generation_config(self) -> OpenAPIConfig:
        config = cast('OpenAPIConfig', self._openapi_config)
        security_schemes = dict(config.security_schemes)
        applications = [self]
        while applications:
            app = applications.pop()
            applications.extend(subapp for _prefix, subapp in app._subapps)  # noqa: SLF001
            if app._security_config is None:  # noqa: SLF001
                continue
            for scheme in app._security_config.schemes:  # noqa: SLF001
                existing = security_schemes.get(scheme.name)
                if existing is not None and dict(existing) != scheme.openapi_schema:
                    msg = f'Conflicting OpenAPI security scheme: {scheme.name!r}'
                    raise ValueError(msg)
                security_schemes[scheme.name] = scheme.openapi_schema
        return replace(config, security_schemes=security_schemes)

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
            if response._eof_sent:  # noqa: SLF001
                await self._run_background(response, request)
            return
        await response._send(response_send, server_info=server_info)  # noqa: SLF001
        if request is not None:
            await self._run_background(response, request)

    @staticmethod
    async def _run_background(response: Response | StreamResponse, request: Request) -> None:
        background = response.background
        if background is None:
            return
        try:
            await background()
        except Exception as exc:
            logger.exception('Unhandled exception in response background task', exc_info=exc)
            _raise_server_exception_for_tests(request.scope, exc)

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


def _bind_openapi_security(
    openapi_config: OpenAPIConfig | None,
    security: SecurityConfig | None,
) -> OpenAPIConfig | None:
    if openapi_config is None or security is None:
        return openapi_config

    security_schemes = dict(openapi_config.security_schemes)
    for scheme in security.schemes:
        existing = security_schemes.get(scheme.name)
        if existing is not None and dict(existing) != scheme.openapi_schema:
            msg = f'Conflicting OpenAPI security scheme: {scheme.name!r}'
            raise ValueError(msg)
        security_schemes[scheme.name] = scheme.openapi_schema

    configured_requirements = tuple(
        {name: tuple(scopes) for name, scopes in requirement.items()}
        for requirement in openapi_config.security
    )
    runtime_requirements = tuple(security.requirements)
    if configured_requirements and configured_requirements != runtime_requirements:
        msg = 'OpenAPIConfig.security conflicts with SecurityConfig.requirements'
        raise ValueError(msg)
    return replace(
        openapi_config,
        security_schemes=security_schemes,
        security=runtime_requirements,
    )


def _raise_server_exception_for_tests(scope: ASGIScope, exc: Exception) -> None:
    if scope.get('_rapidy_raise_server_exceptions'):
        raise exc


class _TrackingSend:
    __slots__ = ('_send', 'completed', 'started')

    def __init__(self, send: Send) -> None:
        self._send = send
        self.started = False
        self.completed = False

    async def __call__(self, message: dict[str, Any]) -> None:
        message_type = message.get('type')
        completed_body = message_type in {'http.response.body', 'http.response.zerocopysend'} and not message.get(
            'more_body', False
        )
        if message_type == 'http.response.start':
            self.started = True
        elif completed_body or message_type == 'http.response.pathsend':
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
