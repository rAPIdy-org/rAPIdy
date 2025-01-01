import contextlib
import logging
import warnings
from typing import Any, AsyncGenerator, Callable, Coroutine, Iterable, Iterator, List, Mapping, Optional, Tuple

from aiohttp.log import web_logger
from aiohttp.web_app import (
    Application as AiohttpApplication,
    CleanupError,
)
from aiohttp.web_middlewares import _fix_request_current_app
from aiohttp.web_request import Request

from rapidy._base_exceptions import RapidyException
from rapidy.constants import CLIENT_MAX_SIZE
from rapidy.endpoint_handlers.http.handlers import middleware_validation_wrapper
from rapidy.enums import HeaderName
from rapidy.lifespan import Lifespan, LifespanCTX, LifespanHook
from rapidy.routing.http.base import BaseHTTPRouter
from rapidy.typedefs import HTTPRouterType, Middleware
from rapidy.version import SERVER_INFO
from rapidy.web_middlewares import get_middleware_attr_data, is_aiohttp_new_style_middleware, is_rapidy_middleware
from rapidy.web_response import StreamResponse
from rapidy.web_urldispatcher import UrlDispatcher

__all__ = (
    'Application',
    'CleanupError',
)

InnerDeco = Callable[[], Coroutine[Any, Any, None]]


class RouterTypeError(RapidyException):
    message = """
    `route_handler` must be a subclass of HTTPRouter
    If you are using `web.View` - make sure it is under the `@view` / `@get` / `@post` /... decorator.

    >>>
    >>> from rapidy.http import get, view
    >>>
    >>> @view("/")  # <-- view deco
    >>> class MyView(web.View):
    >>>     async def get(self) -> None: pass
    >>>
    >>> @get("/")  # <-- get deco
    >>> class MyView(web.View):
    >>>     async def get(self) -> None: pass
    """


def server_info_wrapper(*, show_info: bool = False) -> Callable[[Any], InnerDeco]:
    def deco(prepare_headers_bound_method: Any) -> InnerDeco:
        response = prepare_headers_bound_method.__self__

        async def inner() -> None:
            await prepare_headers_bound_method()
            if show_info:
                response._headers[HeaderName.server.value] = SERVER_INFO  # noqa: SLF001
            else:
                response._headers.pop(HeaderName.server)  # noqa: SLF001

        return inner

    return deco


class Application(AiohttpApplication):
    """Overridden aiohttp Application."""

    def __init__(
        self,
        *,
        logger: logging.Logger = web_logger,
        middlewares: Optional[Iterable[Middleware]] = None,
        handler_args: Optional[Mapping[str, Any]] = None,
        client_max_size: int = CLIENT_MAX_SIZE,
        server_info_in_response: bool = False,
        lifespan: Optional[List[LifespanCTX]] = None,
        on_startup: Optional[List[LifespanHook]] = None,
        on_shutdown: Optional[List[LifespanHook]] = None,
        on_cleanup: Optional[List[LifespanHook]] = None,
        # routes
        http_route_handlers: Iterable[HTTPRouterType] = (),
    ) -> None:
        """Create an `rapidy` Application instance.

        Args:
            logger:
                logging.Logger instance for storing application logs.
                By default, the value is logging.getLogger("aiohttp.web").
            middlewares:
                List of middleware factories.
            handler_args:
                Mapping object that overrides keyword arguments of Application.make_handler()
            client_max_size:
                Client`s maximum size in a request, in bytes.
                If a POST request exceeds this value, it raises an HTTPRequestEntityTooLarge exception.
            server_info_in_response:
                Boolean value indicating whether to give the server information in the `Server`
                response header in each request.
                > 'Server': 'Python/3.12.0 rapidy/1.0.0 aiohttp/4.0.0'
            lifespan:
                A list of callables returning async context managers,
                wrapping the lifespan of the application.
                >>> @asynccontextmanager
                >>> async def lifespan_ctx(app: web.Application) -> AsyncGenerator[None, None]:
                >>>     try:
                >>>         await startup_func()
                >>>             yield
                >>>     finally:
                >>>         await shutdown_func()

                You can set this in two ways:
                >>> app = web.Application(lifespan=[lifespan_ctx, ...], ...)
                or
                >>> app.lifespan.append(lifespan_ctx)
            on_startup:
                A sequence of `rapidy.typedefs.LifespanHook` called during application startup.
                Developers may use this to run background tasks in the event loop
                along with the application`s request handler just after the application start-up.
                >>> def on_startup(app):
                >>>     pass

                >>> def on_startup():
                >>>     pass

                >>> async def on_startup(app):
                >>>     pass

                >>> async def on_startup():
                >>>     pass

                You can set this in two ways:
                >>> app = web.Application(on_startup=[on_startup, ...], ...)
                or
                >>> app.lifespan.on_startup.append(on_startup)
            on_shutdown:
                A sequence of `rapidy.types.LifespanHook` called during application shutdown.
                Developers may use this for gracefully closing long running connections,
                e.g. websockets and data streaming.
                >>> def on_shutdown(app):
                >>>     pass

                >>> def on_shutdown():
                >>>     pass

                >>> async def on_shutdown(app):
                >>>     pass

                >>> async def on_shutdown():
                >>>     pass
                You can set this in two ways:
                >>> app = web.Application(on_shutdown=[on_shutdown, ...], ...)
                or
                >>> app.lifespan.on_shutdown.append(on_shutdown)
            on_cleanup:
                A sequence of `rapidy.types.LifespanHook` called during application cleanup.
                Developers may use this for gracefully closing connections to database server etc.
                Signal handlers should have the following signature:
                >>> def on_cleanup(app):
                >>>     pass

                >>> def on_cleanup():
                >>>     pass

                >>> async def on_cleanup(app):
                >>>     pass

                >>> async def on_cleanup():
                >>>     pass

                >>> app = web.Application(on_cleanup=[on_cleanup, ...], ...)
            http_route_handlers:
                A iterable of `rapidy.routing.http.base.BaseHTTPRouter`.
                All passed handlers will be registered in the application.
                >>> from rapidy import web
                >>> from rapidy.http import get, HTTPRouterType
                >>>
                >>> @get('/app_path1')
                >>> async def app_handler1() -> None: pass
                >>>
                >>> async def app_handler2() -> None: pass
                >>>
                >>> @get('/router_path1')
                >>> async def router_handler1() -> None: pass
                >>>
                >>> async def router_handler2() -> None: pass
                >>>
                >>> api_router = HTTPRouterType(
                >>>     '/api',
                >>>     route_handlers=[
                >>>         router_handler1,
                >>>         get.handler('/router_path2', router_handler2),
                >>>     ],
                >>> )
                >>>
                >>> app = web.Application(
                >>>     http_route_handlers=[
                >>>         api_router,  # add router
                >>>         app_handler1,
                >>>         get.handler('/app_path2', app_handler2),
                >>>     ]
                >>> )
        """
        super().__init__(
            logger=logger,
            middlewares=middlewares or [],
            handler_args=handler_args,
            client_max_size=client_max_size,
        )

        self.lifespan = Lifespan(
            app=self,
            lifespan_managers=lifespan or [],
            on_startup=on_startup or [],
            on_shutdown=on_shutdown or [],
            on_cleanup=on_cleanup or [],
        )

        self._cleanup_ctx.insert(0, self._create_lifespan_cleanup_ctx(self.lifespan))

        # NOTE: override aiohttp router
        self._router = UrlDispatcher()

        # It is hidden by default, as I believe showing server information is a potential vulnerability.
        self._hide_server_info_deco = server_info_wrapper(show_info=server_info_in_response)

        self.add_http_routers(http_route_handlers)

    def add_http_router(self, http_router: HTTPRouterType) -> None:
        """Add http router."""
        # mypy is bullshit - class decorators that change type don't work
        # we need to do this check to protect the developers
        if not isinstance(http_router, BaseHTTPRouter):
            raise RouterTypeError

        http_router.register(application=self)

    def add_http_routers(self, route_handlers: Iterable[HTTPRouterType]) -> None:
        """Add http routers."""
        for route_handler in route_handlers:
            self.add_http_router(route_handler)

    @property
    def router(self) -> UrlDispatcher:
        """Return overridden aiohttp UrlDispatcher."""
        return self._router

    def _create_lifespan_cleanup_ctx(self, lifespan: Lifespan) -> Callable[['Application'], AsyncGenerator[None, None]]:
        async def lifespan_cleanup_ctx(app: 'Application') -> AsyncGenerator[None, None]:  # noqa: ARG001
            lifespan_ctx_generator = lifespan.ctx_manager().gen

            await lifespan_ctx_generator.__anext__()

            yield

            with contextlib.suppress(StopAsyncIteration):
                await lifespan_ctx_generator.__anext__()

        return lifespan_cleanup_ctx

    def _prepare_middleware(self) -> Iterator[Tuple[Middleware, bool]]:
        for middleware in reversed(self._middlewares):
            if is_aiohttp_new_style_middleware(middleware):
                if is_rapidy_middleware(middleware):
                    m_attr_data = get_middleware_attr_data(middleware)

                    middleware = middleware_validation_wrapper(  # noqa: PLW2901
                        middleware,
                        response_validate=m_attr_data.response_validate,
                        response_type=m_attr_data.response_type,
                        response_content_type=m_attr_data.response_content_type,
                        response_charset=m_attr_data.response_charset,
                        response_zlib_executor=m_attr_data.response_zlib_executor,
                        response_zlib_executor_size=m_attr_data.response_zlib_executor_size,
                        response_include_fields=m_attr_data.response_include_fields,
                        response_exclude_fields=m_attr_data.response_exclude_fields,
                        response_by_alias=m_attr_data.response_by_alias,
                        response_exclude_unset=m_attr_data.response_exclude_unset,
                        response_exclude_defaults=m_attr_data.response_exclude_defaults,
                        response_exclude_none=m_attr_data.response_exclude_none,
                        response_custom_encoder=m_attr_data.response_custom_encoder,
                        response_json_encoder=m_attr_data.response_json_encoder,
                    )
                yield middleware, True
            else:
                warnings.warn(
                    '`rapidy` does not support Old-style middleware - please use @middleware decorator.\n'
                    'If you are using middlewares with a nested middlewares wrapped by @middleware -\n'
                    'make sure that in Application(middlewares=[...]) you pass its instance.\n\n'
                    'Example:\n'
                    '>> app = Application(middlewares=[parametrized_middleware(<some_attr>=<some_value>)])',
                    DeprecationWarning,
                    stacklevel=2,
                )
                yield middleware, False

        yield _fix_request_current_app(self), True

    async def _prepare_response(self, resp: StreamResponse) -> StreamResponse:
        resp._prepare_headers = self._hide_server_info_deco(resp._prepare_headers)  # noqa: SLF001
        return resp

    async def _handle(self, request: Request) -> StreamResponse:
        resp = await super()._handle(request)
        await self._prepare_response(resp)
        return resp
