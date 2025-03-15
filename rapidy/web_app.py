import contextlib
import logging
import warnings
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Coroutine,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Tuple,
    TypeVar,
    Union,
)

from aiohttp.log import web_logger
from aiohttp.web_app import (
    Application as AiohttpApplication,
    CleanupError,
)
from aiohttp.web_middlewares import _fix_request_current_app
from aiohttp.web_request import Request

from rapidy.constants import CLIENT_MAX_SIZE
from rapidy.endpoint_handlers.http.handlers import middleware_validation_wrapper
from rapidy.enums import HeaderName
from rapidy.lifespan import Lifespan, LifespanCTX, LifespanHook
from rapidy.routing.http.base import raise_if_not_base_http_router
from rapidy.typedefs import BaseHTTPRouterType, Middleware
from rapidy.version import SERVER_INFO
from rapidy.web_middlewares import get_middleware_attr_data, is_aiohttp_new_style_middleware, is_rapidy_middleware
from rapidy.web_response import StreamResponse
from rapidy.web_urldispatcher import UrlDispatcher

__all__ = (
    'Application',
    'CleanupError',
)

InnerDeco = Callable[[], Coroutine[Any, Any, None]]

TApplication = TypeVar('TApplication')


def ignore_inherited_warning_aio_init_subclass() -> Callable[[TApplication], Callable[[], None]]:
    """Suppresses `DeprecationWarning` when a subclass of `AiohttpApplication` is initialized.

    Returns:
        Callable[[TApplication], Callable[[TApplication], None]]: A function that suppresses warnings when called.
    """

    def inner(cls: TApplication) -> Callable[[], None]:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', DeprecationWarning)
            return cls.__init_subclass__

    return inner


AiohttpApplication.__init_subclass__ = ignore_inherited_warning_aio_init_subclass


def server_info_wrapper(*, show_info: bool = False) -> Callable[[Any], InnerDeco]:
    """Wraps a method to include server information in the response header.

    Args:
        show_info (bool): Whether to show server information in the response header.

    Returns:
        Callable: A decorator function to modify headers.
    """

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
    """Custom Application class for handling aiohttp web app lifecycle.

    This class overrides the default `aiohttp.Application` and provides additional functionality
    like lifespan management, custom middleware handling, and server info in response headers.

    Attributes:
        lifespan (Lifespan): An instance of the Lifespan class that manages the lifecycle of the application.
        _cleanup_ctx (List[Callable[[Application], AsyncGenerator[None, None]]]): Context managers for cleanup
          when the application is shut down.
        _router (UrlDispatcher): The URL dispatcher responsible for routing requests.
        _hide_server_info_deco (Callable): A decorator function to control whether server information is included in
          response headers.

    Methods:
        add_http_router(http_router: BaseHTTPRouterType) -> None: Adds a single HTTP router to the app.
        add_http_routers(route_handlers: Iterable[BaseHTTPRouterType]) -> None: Adds multiple HTTP routers.
        router() -> UrlDispatcher: Returns the overridden aiohttp `UrlDispatcher`.
    """

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
        # FIXME(daniil_grois): Fix `Any` after mypy improves type checking for cls deco
        http_route_handlers: Iterable[Union[BaseHTTPRouterType, Any]] = (),
    ) -> None:
        """Initializes the Application instance with various configuration options.

        Args:
            logger (logging.Logger): Logger instance for application logs.
            middlewares (Optional[Iterable[Middleware]]):  list of middleware applied to the Application.
            handler_args (Optional[Mapping[str, Any]]): Arguments to pass to `make_handler()`.
            client_max_size: Client`s maximum size in a request, in bytes.
            server_info_in_response (bool): Whether to include server info in response headers.
            lifespan: List of asynchronous context managers that support application lifecycle management.
                >>> @asynccontextmanager
                >>> async def lifespan_ctx(rapidy: Rapidy) -> AsyncGenerator[None, None]:
                >>>     try:
                >>>         await startup_func()
                >>>             yield
                >>>     finally:
                >>>         await shutdown_func()
                You can set this in two ways:
                >>> rapidy = Rapidy(lifespan=[lifespan_ctx, ...], ...)
                or
                >>> rapidy.lifespan.append(lifespan_ctx)
            on_startup: A sequence of `rapidy.typedefs.LifespanHook` called during application startup.
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
                >>> rapidy = Rapidy(on_startup=[on_startup, ...], ...)
                or
                >>> rapidy.lifespan.on_startup.append(on_startup)
            on_shutdown: A sequence of `rapidy.types.LifespanHook` called during application shutdown.
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
                >>> rapidy = Rapidy(on_shutdown=[on_shutdown, ...], ...)
                or
                >>> rapidy.lifespan.on_shutdown.append(on_shutdown)
            on_cleanup: A sequence of `rapidy.types.LifespanHook` called during application cleanup.
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

                >>> rapidy = Rapidy(on_cleanup=[on_cleanup, ...], ...)
            http_route_handlers (Iterable[BaseHTTPRouterType]): HTTP route handlers to register.
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

    def add_http_router(
        self,
        # FIXME(daniil_grois): Fix `Any` after mypy improves type checking for cls deco
        http_router: Union[BaseHTTPRouterType, Any],
    ) -> None:
        """Adds an HTTP router to the application.

        Args:
            http_router (BaseHTTPRouterType): The HTTP router to add.

        Raises:
            RouterTypeError: If the provided `http_router` is not an instance of `BaseHTTPRouter`.
        """
        raise_if_not_base_http_router(http_router)

        http_router.route_register(application=self)

    def add_http_routers(
        self,
        # FIXME: Fix `Any` after mypy improves type checking for cls deco
        route_handlers: Iterable[Union[BaseHTTPRouterType, Any]],
    ) -> None:
        """Adds multiple HTTP routers to the application.

        Args:
            route_handlers (Iterable[BaseHTTPRouterType]): A list of HTTP routers to add.
        """
        for route_handler in route_handlers:
            self.add_http_router(route_handler)

    @property
    def router(self) -> UrlDispatcher:
        """Returns the overridden aiohttp UrlDispatcher.

        Returns:
            UrlDispatcher: The URL dispatcher for routing requests.
        """
        return self._router

    def _create_lifespan_cleanup_ctx(self, lifespan: Lifespan) -> Callable[['Application'], AsyncGenerator[None, None]]:
        """Creates a cleanup context manager for lifespan management.

        Args:
            lifespan (Lifespan): The lifespan object for managing application lifespan.

        Returns:
            Callable: A function that manages lifespan cleanup.
        """

        async def lifespan_cleanup_ctx(app: 'Application') -> AsyncGenerator[None, None]:  # noqa: ARG001
            lifespan_ctx_generator = lifespan.ctx_manager().gen

            await lifespan_ctx_generator.__anext__()

            yield

            with contextlib.suppress(StopAsyncIteration):
                await lifespan_ctx_generator.__anext__()

        return lifespan_cleanup_ctx

    def _prepare_middleware(self) -> Iterator[Tuple[Middleware, bool]]:
        """Prepares middleware for the application, handling different middleware styles.

        Yields:
            Tuple[Middleware, bool]: A tuple containing the middleware and a boolean indicating
            whether it is a valid middleware.
        """
        for middleware in reversed(self._middlewares):
            if is_aiohttp_new_style_middleware(middleware):
                if is_rapidy_middleware(middleware):
                    m_attr_data = get_middleware_attr_data(middleware)

                    middleware = middleware_validation_wrapper(  # noqa: PLW2901
                        middleware,
                        status_code=m_attr_data.status_code,
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
        """Prepares the response, modifying headers as needed.

        Args:
            resp (StreamResponse): The response to modify.

        Returns:
            StreamResponse: The modified response.
        """
        resp._prepare_headers = self._hide_server_info_deco(resp._prepare_headers)  # noqa: SLF001
        return resp

    async def _handle(self, request: Request) -> StreamResponse:
        resp = await super()._handle(request)
        await self._prepare_response(resp)
        return resp
