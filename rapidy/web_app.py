import asyncio
import logging
import warnings
from functools import partial, update_wrapper
from types import FunctionType
from typing import Any, Dict, Iterable, Iterator, Mapping, Optional, Tuple

from aiohttp.abc import AbstractMatchInfo, AbstractView
from aiohttp.log import web_logger
from aiohttp.web_app import Application as AiohttpApplication, CleanupError
from aiohttp.web_middlewares import _fix_request_current_app
from aiohttp.web_urldispatcher import MatchInfoError

from rapidy import hdrs
from rapidy._annotation_container import AnnotationContainer, create_annotation_container, HandlerEnumType
from rapidy._web_request_validation import _validate_request
from rapidy.constants import CLIENT_MAX_SIZE
from rapidy.typedefs import Handler, Middleware
from rapidy.web_request import Request
from rapidy.web_response import StreamResponse
from rapidy.web_urldispatcher import StaticResource, UrlDispatcher

__all__ = (
    'Application',
    'CleanupError',
)


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
        self._server_info_in_response = server_info_in_response

    @property
    def router(self) -> UrlDispatcher:
        return self._router

    def _add_middleware_annotation_container(self, middleware: Middleware) -> None:
        self._middleware_annotation_containers[id(middleware)] = create_annotation_container(
            middleware,
            handler_type=HandlerEnumType.middleware,
        )

    def _get_middleware_annotation_container(self, middleware: Middleware) -> Optional[AnnotationContainer]:
        return self._middleware_annotation_containers.get(id(middleware))

    def _prepare_middleware(self) -> Iterator[Tuple[Middleware, bool]]:  # FIXME: refactor
        for middleware in reversed(self._middlewares):
            if getattr(middleware, '__middleware_version__', None) == 1:
                self._add_middleware_annotation_container(middleware)
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

    async def _handle(self, request: Request) -> StreamResponse:  # noqa: C901 WPS212  # FIXME: refactor
        loop = asyncio.get_event_loop()
        debug = loop.get_debug()
        match_info = await self._router.resolve(request)
        if debug:  # pragma: no cover
            if not isinstance(match_info, AbstractMatchInfo):
                raise TypeError(
                    'match_info should be AbstractMatchInfo '
                    'instance, not {!r}'.format(match_info),
                )
        match_info.add_app(self)

        match_info.freeze()

        resp = None
        request._match_info = match_info
        expect = request.headers.get(hdrs.EXPECT)
        if expect:  # aiohttp code  # pragma: no cover
            resp = await match_info.expect_handler(request)
            await request.writer.drain()

        if resp is None:
            handler = match_info.handler

            if isinstance(match_info, MatchInfoError):
                return await handler(request)

            if self._run_middlewares:
                # FIXME: refactor
                if isinstance(match_info.route.resource, StaticResource):
                    async def w_handler(request: Request) -> StreamResponse:  # noqa: WPS442
                        return await handler(request)
                else:
                    async def w_handler(request: Request) -> StreamResponse:  # noqa: WPS440 WPS442
                        return await self._get_handler_response(request, handler)

                for app in match_info.apps[::-1]:
                    for middleware, new_style in app._middlewares_handlers:
                        if new_style:
                            validated_request_data_for_middleware = await self._validate_request_for_middleware(
                                app=app, request=request, middleware=middleware,
                            )
                            w_handler = update_wrapper(
                                partial(middleware, handler=w_handler, **validated_request_data_for_middleware),
                                w_handler,
                            )
                        else:
                            w_handler = await middleware(app, w_handler)

                resp = await w_handler(request)

            else:
                # FIXME: refactor
                if isinstance(match_info.route.resource, StaticResource):
                    return await handler(request)
                else:
                    return await self._get_handler_response(request, handler)

        return resp

    async def _get_handler_response(
            self,
            request: Request,
            handler: Handler,
    ) -> StreamResponse:
        if isinstance(handler, FunctionType):
            annotation_container = request._match_info.route.get_method_container(request.method)

            validate_request_data_for_handler = await _validate_request(
                request=request,
                annotation_container=annotation_container,
                errors_response_field_name=self._client_errors_response_field_name,
            )

            if annotation_container.request_exists:
                validate_request_data_for_handler[annotation_container.request_param_name] = request

            return await handler(**validate_request_data_for_handler)

        if issubclass(handler, AbstractView):  # type: ignore[arg-type]
            return await handler(request)

        raise ValueError('Unknown handler type')

    async def _validate_request_for_middleware(
            self,
            app: 'Application',
            request: Request,
            middleware: Middleware,
    ) -> Dict[str, Any]:
        annotation_container = app._get_middleware_annotation_container(middleware)
        if annotation_container:
            return await _validate_request(
                request=request,
                annotation_container=annotation_container,
                errors_response_field_name=self._client_errors_response_field_name,
            )

        return {}
