import asyncio
import logging
import warnings
from typing import Any, Callable, Coroutine, Dict, Iterable, Iterator, Mapping, Optional, Tuple

from aiohttp.log import web_logger
from aiohttp.web_app import Application as AiohttpApplication, CleanupError
from aiohttp.web_middlewares import _fix_request_current_app
from aiohttp.web_request import Request

from rapidy import hdrs
from rapidy._annotation_container import AnnotationContainer
from rapidy._version import SERVER_INFO
from rapidy._web_request_validation import middleware_validation_wrapper
from rapidy.constants import CLIENT_MAX_SIZE
from rapidy.typedefs import Middleware
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
            logger: logging.Logger = web_logger,
            router: Optional[UrlDispatcher] = None,
            middlewares: Iterable[Middleware] = (),
            handler_args: Optional[Mapping[str, Any]] = None,
            client_max_size: int = CLIENT_MAX_SIZE,
            client_errors_response_field_name: str = 'errors',
            loop: Optional[asyncio.AbstractEventLoop] = None,
            debug: Any = ...,
            server_info_in_response: bool = False,
    ) -> None:
        # TODO: Add a check that in body extractors the size does not exceed the client size

        super().__init__(
            logger=logger,
            router=router,
            middlewares=middlewares,
            handler_args=handler_args,
            client_max_size=client_max_size,
            loop=loop,
            debug=debug,
        )

        # NOTE: override aiohttp router
        self._router = UrlDispatcher()

        self._client_errors_response_field_name = client_errors_response_field_name

        self._middleware_annotation_containers: Dict[int, AnnotationContainer] = {}

        # It is hidden by default, as I believe showing server information is a potential vulnerability.
        self._hide_server_info_deco = hide_server_info_deco(server_info_in_response)

    @property
    def router(self) -> UrlDispatcher:
        return self._router

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
        request._cache['errors_response_field_name'] = self._client_errors_response_field_name  # FIXME

        resp = await super()._handle(request)

        await self._prepare_response(resp)

        return resp
