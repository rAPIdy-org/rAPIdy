import logging
import warnings
from typing import Any, AsyncGenerator, Callable, Coroutine, Iterable, Iterator, List, Mapping, Optional, Tuple

from aiohttp.log import web_logger
from aiohttp.web_app import Application as AiohttpApplication, CleanupError
from aiohttp.web_middlewares import _fix_request_current_app
from aiohttp.web_request import Request
from typing_extensions import Annotated, Doc

from rapidy import hdrs
from rapidy._lifespan import Lifespan, LifespanCTX, LifespanHook
from rapidy._request_validation_wrappers import middleware_validation_wrapper
from rapidy.typedefs import Middleware
from rapidy.version import SERVER_INFO
from rapidy.web_middlewares import is_aiohttp_new_style_middleware, is_rapidy_middleware
from rapidy.web_response import StreamResponse
from rapidy.web_urldispatcher import UrlDispatcher

__all__ = (
    'Application',
    'CleanupError',
)


InnerDeco = Callable[[], Coroutine[Any, Any, None]]


def hide_server_info_deco(show_server_info_in_response: bool = False) -> Callable[[Any], InnerDeco]:
    def deco(prepare_headers_bound_method: Any) -> InnerDeco:
        response = prepare_headers_bound_method.__self__

        async def inner() -> None:
            await prepare_headers_bound_method()
            if show_server_info_in_response:
                response._headers[hdrs.SERVER] = SERVER_INFO
            else:
                response._headers.pop(hdrs.SERVER)

        return inner

    return deco


class Application(AiohttpApplication):
    def __init__(
            self,
            *,
            logger: Annotated[
                logging.Logger,
                Doc(
                    """
                    logging.Logger instance for storing application logs.

                    By default the value is logging.getLogger("aiohttp.web").
                    """,
                ),
            ] = web_logger,

            middlewares: Annotated[
                Optional[Iterable[Middleware]],
                Doc(
                    """
                    List of middleware factories.
                    """,
                ),
            ] = None,

            handler_args: Annotated[
                Optional[Mapping[str, Any]],
                Doc(
                    """
                    Mapping object that overrides keyword arguments of Application.make_handler()
                    """,
                ),
            ] = None,

            client_max_size: Annotated[
                int,
                Doc(
                    """
                    Client’s maximum size in a request, in bytes.

                    If a POST request exceeds this value, it raises an HTTPRequestEntityTooLarge exception.
                    """,
                ),
            ] = 1024**2,

            server_info_in_response: Annotated[
                bool,
                Doc(
                    """
                    Boolean value indicating whether or not to give the
                    server information in the `Server` response header in each request.

                    Default value is False.

                    Examples:
                        response_headers = {
                            'Server': 'Python/3.12.0 rapidy/1.0.0 aiohttp/4.0.0',
                            ...
                        }
                    """,
                ),
            ] = False,

            lifespan: Annotated[
                Optional[List[LifespanCTX]],
                Doc(
                    """
                    A list of callables returning async context managers,
                    wrapping the lifespan of the application.

                    Examples:
                        >>> @asynccontextmanager
                        >>> async def lifespan_ctx(app: web.Application) -> AsyncGenerator[None, None]:
                        >>> try:
                        >>>     await startup_func()
                        >>>         yield
                        >>> finally:
                        >>>     await shutdown_func()

                        You can set this in two ways:
                        >>> app = web.Application(lifespan=[lifespan_ctx, ...], ...)
                        or
                        >>> app.lifespan.append(lifespan_ctx)
                    """,
                ),
            ] = None,

            on_startup: Annotated[
                Optional[List[LifespanHook]],
                Doc(
                    """
                    A sequence of `rapidy.typedefs.LifespanHook` called during application startup.

                    Developers may use this to run background tasks in the event loop
                    along with the application’s request handler just after the application start-up.

                    Examples:
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
                    """,
                ),
            ] = None,

            on_shutdown: Annotated[
                Optional[List[LifespanHook]],
                Doc(
                    """
                    A sequence of `rapidy.types.LifespanHook` called during application shutdown.

                    Developers may use this for gracefully closing long running connections,
                    e.g. websockets and data streaming.

                    Examples:
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

                    """,
                ),
            ] = None,

            on_cleanup: Annotated[
                Optional[List[LifespanHook]],
                Doc(
                    """
                    A sequence of `rapidy.types.LifespanHook` called during application cleanup.

                    Developers may use this for gracefully closing connections to database server etc.
                    Signal handlers should have the following signature:

                    Examples:
                        >>> def on_cleanup(app):
                        >>>     pass

                        >>> def on_cleanup():
                        >>>     pass

                        >>> async def on_cleanup(app):
                        >>>     pass

                        >>> async def on_cleanup():
                        >>>     pass

                        >>> app = web.Application(on_cleanup=[on_cleanup, ...], ...)
                    """,
                ),
            ] = None,
    ) -> None:
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
        self._hide_server_info_deco = hide_server_info_deco(server_info_in_response)

    @property
    def router(self) -> UrlDispatcher:
        return self._router

    def _create_lifespan_cleanup_ctx(self, lifespan: Lifespan) -> Callable[['Application'], AsyncGenerator[None, None]]:
        async def lifespan_cleanup_ctx(app: 'Application') -> AsyncGenerator[None, None]:
            lifespan_ctx_generator = lifespan.ctx_manager().gen

            await lifespan_ctx_generator.__anext__()

            yield

            try:
                await lifespan_ctx_generator.__anext__()
            except StopAsyncIteration:
                pass

        return lifespan_cleanup_ctx

    def _prepare_middleware(self) -> Iterator[Tuple[Middleware, bool]]:
        for middleware in reversed(self._middlewares):
            if is_aiohttp_new_style_middleware(middleware):
                if is_rapidy_middleware(middleware):
                    middleware = middleware_validation_wrapper(middleware)
                yield middleware, True
            else:
                warnings.warn(
                    'rAPIdy does not support Old-style middleware - please use @middleware decorator.\n'
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
        resp._prepare_headers = self._hide_server_info_deco(resp._prepare_headers)
        return resp

    async def _handle(self, request: Request) -> StreamResponse:
        resp = await super()._handle(request)
        await self._prepare_response(resp)
        return resp
