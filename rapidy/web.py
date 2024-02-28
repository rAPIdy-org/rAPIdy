import asyncio
import json
import logging
from functools import partial, update_wrapper
from typing import Any, Dict, Iterable, Mapping, Optional, Union

from aiohttp.abc import AbstractMatchInfo
from aiohttp.helpers import AppKey
from aiohttp.log import web_logger
from aiohttp.typedefs import Middleware
from aiohttp.web import run_app
from aiohttp.web_app import _AppSignal, _MiddlewaresHandlers, _RespPrepareSignal, _Subapps, CleanupContext
from aiohttp.web_urldispatcher import MatchInfoError, UrlMappingMatchInfo
from aiosignal import Signal
from frozenlist import FrozenList

from rapidy import hdrs
from rapidy._client_errors import _normalize_errors
from rapidy.constants import CLIENT_MAX_SIZE
from rapidy.media_types import ApplicationJSON
from rapidy.request_params import (
    BytesBody,
    Cookie,
    CookieRaw,
    CookieSchema,
    FormDataBody,
    FormDataBodyRaw,
    FormDataBodySchema,
    Header,
    HeaderRaw,
    HeaderSchema,
    JsonBody,
    JsonBodyRaw,
    JsonBodySchema,
    MultipartBody,
    MultipartBodyRaw,
    MultipartBodySchema,
    Path,
    PathRaw,
    PathSchema,
    Query,
    QueryRaw,
    QuerySchema,
    StreamBody,
    TextBody,
)
from rapidy.web_app import Application as AiohttpApplication, CleanupError
from rapidy.web_exceptions import (
    HTTPAccepted,
    HTTPBadGateway,
    HTTPBadRequest,
    HTTPClientError,
    HTTPConflict,
    HTTPCreated,
    HTTPError,
    HTTPException,
    HTTPExpectationFailed,
    HTTPFailedDependency,
    HTTPForbidden,
    HTTPFound,
    HTTPGatewayTimeout,
    HTTPGone,
    HTTPInsufficientStorage,
    HTTPInternalServerError,
    HTTPLengthRequired,
    HTTPMethodNotAllowed,
    HTTPMisdirectedRequest,
    HTTPMovedPermanently,
    HTTPMultipleChoices,
    HTTPNetworkAuthenticationRequired,
    HTTPNoContent,
    HTTPNonAuthoritativeInformation,
    HTTPNotAcceptable,
    HTTPNotExtended,
    HTTPNotFound,
    HTTPNotImplemented,
    HTTPNotModified,
    HTTPOk,
    HTTPPartialContent,
    HTTPPaymentRequired,
    HTTPPermanentRedirect,
    HTTPPreconditionFailed,
    HTTPPreconditionRequired,
    HTTPProxyAuthenticationRequired,
    HTTPRedirection,
    HTTPRequestEntityTooLarge,
    HTTPRequestHeaderFieldsTooLarge,
    HTTPRequestRangeNotSatisfiable,
    HTTPRequestTimeout,
    HTTPRequestURITooLong,
    HTTPResetContent,
    HTTPSeeOther,
    HTTPServerError,
    HTTPServiceUnavailable,
    HTTPSuccessful,
    HTTPTemporaryRedirect,
    HTTPTooManyRequests,
    HTTPUnauthorized,
    HTTPUnavailableForLegalReasons,
    HTTPUnprocessableEntity,
    HTTPUnsupportedMediaType,
    HTTPUpgradeRequired,
    HTTPUseProxy,
    HTTPVariantAlsoNegotiates,
    HTTPVersionNotSupported,
)
from rapidy.web_middlewares import middleware, normalize_path_middleware
from rapidy.web_request import BaseRequest, FileField, Request
from rapidy.web_response import ContentCoding, json_response, Response, StreamResponse
from rapidy.web_routedef import (
    AbstractRouteDef,
    delete,
    get,
    head,
    options,
    patch,
    post,
    put,
    route,
    RouteDef,
    RouteTableDef,
    static,
    StaticDef,
    view,
)
from rapidy.web_runner import (
    AppRunner,
    BaseRunner,
    BaseSite,
    GracefulExit,
    NamedPipeSite,
    ServerRunner,
    SockSite,
    TCPSite,
    UnixSite,
)
from rapidy.web_urldispatcher import UrlDispatcher, View

__all__ = (
    # web_app
    'Application',
    'CleanupError',
    # web_exceptions
    'HTTPAccepted',
    'HTTPBadGateway',
    'HTTPBadRequest',
    'HTTPClientError',
    'HTTPConflict',
    'HTTPCreated',
    'HTTPError',
    'HTTPException',
    'HTTPExpectationFailed',
    'HTTPFailedDependency',
    'HTTPForbidden',
    'HTTPFound',
    'HTTPGatewayTimeout',
    'HTTPGone',
    'HTTPInsufficientStorage',
    'HTTPInternalServerError',
    'HTTPLengthRequired',
    'HTTPMethodNotAllowed',
    'HTTPMisdirectedRequest',
    'HTTPMovedPermanently',
    'HTTPMultipleChoices',
    'HTTPNetworkAuthenticationRequired',
    'HTTPNoContent',
    'HTTPNonAuthoritativeInformation',
    'HTTPNotAcceptable',
    'HTTPNotExtended',
    'HTTPNotFound',
    'HTTPNotImplemented',
    'HTTPNotModified',
    'HTTPOk',
    'HTTPPartialContent',
    'HTTPPaymentRequired',
    'HTTPPermanentRedirect',
    'HTTPPreconditionFailed',
    'HTTPPreconditionRequired',
    'HTTPProxyAuthenticationRequired',
    'HTTPRedirection',
    'HTTPRequestEntityTooLarge',
    'HTTPRequestHeaderFieldsTooLarge',
    'HTTPRequestRangeNotSatisfiable',
    'HTTPRequestTimeout',
    'HTTPRequestURITooLong',
    'HTTPResetContent',
    'HTTPSeeOther',
    'HTTPServerError',
    'HTTPServiceUnavailable',
    'HTTPSuccessful',
    'HTTPTemporaryRedirect',
    'HTTPTooManyRequests',
    'HTTPUnauthorized',
    'HTTPUnavailableForLegalReasons',
    'HTTPUnprocessableEntity',
    'HTTPUnsupportedMediaType',
    'HTTPUpgradeRequired',
    'HTTPUseProxy',
    'HTTPVariantAlsoNegotiates',
    'HTTPVersionNotSupported',
    # web_middlewares
    'middleware',
    'normalize_path_middleware',
    # web_request
    'BaseRequest',
    'FileField',
    'Request',
    # web_response
    'ContentCoding',
    'Response',
    'StreamResponse',
    'json_response',
    # web_routedef
    'AbstractRouteDef',
    'RouteDef',
    'RouteTableDef',
    'StaticDef',
    'delete',
    'get',
    'head',
    'options',
    'patch',
    'post',
    'put',
    'route',
    'static',
    'view',
    # web_runner
    'AppRunner',
    'BaseRunner',
    'BaseSite',
    'GracefulExit',
    'ServerRunner',
    'SockSite',
    'TCPSite',
    'UnixSite',
    'NamedPipeSite',
    # web_urldispatcher
    'UrlDispatcher',
    'View',
    # web
    'run_app',
    # request_params
    'BytesBody',
    'Cookie',
    'CookieSchema',
    'CookieRaw',
    'FormDataBody',
    'FormDataBodySchema',
    'FormDataBodyRaw',
    'Header',
    'HeaderSchema',
    'HeaderRaw',
    'JsonBody',
    'JsonBodySchema',
    'JsonBodyRaw',
    'MultipartBody',
    'MultipartBodySchema',
    'MultipartBodyRaw',
    'Path',
    'PathSchema',
    'PathRaw',
    'Query',
    'QuerySchema',
    'QueryRaw',
    'StreamBody',
    'TextBody',
)


class Application(AiohttpApplication):
    def __init__(
            self,
            *,
            logger: logging.Logger = web_logger,
            middlewares: Iterable[Middleware] = (),
            handler_args: Optional[Mapping[str, Any]] = None,
            # TODO: Add a check that in body extractors the size does not exceed the client size
            client_max_size: int = CLIENT_MAX_SIZE,
            client_errors_response_field_name: str = 'errors',
    ) -> None:
        self._debug = ...
        self._router = UrlDispatcher()
        self._loop = None
        self._handler_args = handler_args
        self.logger = logger

        self._middlewares: _MiddlewaresHandlers = FrozenList(middlewares)

        self._middlewares_handlers: _MiddlewaresHandlers = None  # initialized on freezing
        self._run_middlewares: Optional[bool] = None  # initialized on freezing

        self._state: Dict[Union[AppKey[Any], str], object] = {}
        self._frozen = False
        self._pre_frozen = False
        self._subapps: _Subapps = []

        self._on_response_prepare: _RespPrepareSignal = Signal(self)
        self._on_startup: _AppSignal = Signal(self)
        self._on_shutdown: _AppSignal = Signal(self)
        self._on_cleanup: _AppSignal = Signal(self)
        self._cleanup_ctx = CleanupContext()
        self._on_startup.append(self._cleanup_ctx._on_startup)
        self._on_cleanup.append(self._cleanup_ctx._on_cleanup)
        self._client_max_size = client_max_size
        self._client_errors_response_field_name = client_errors_response_field_name

    async def _handle(self, request: Request) -> StreamResponse:
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

            if self._run_middlewares:
                for app in match_info.apps[::-1]:
                    for m, new_style in app._middlewares_handlers:
                        if new_style:
                            handler = update_wrapper(
                                partial(m, handler=handler), handler,
                            )
                        else:  # aiohttp code  # pragma: no cover
                            handler = await m(app, handler)

            if isinstance(match_info, MatchInfoError):
                return await handler(request)

            request_validated_data = await self._validate_request(match_info=match_info, request=request)
            resp = await handler(request, **request_validated_data)

        return resp

    async def _validate_request(
            self,
            match_info: UrlMappingMatchInfo,
            request: Request,
    ) -> Dict[str, Any]:
        values, errors = {}, []

        for param_container in match_info.route.get_method_container(request.method):
            param_values, param_errors = await param_container.get_request_data(request)
            if param_errors:
                errors += param_errors
            else:
                values.update(param_values)

        if errors:
            response_errors = {self._client_errors_response_field_name: _normalize_errors(errors)}
            response_errors_body = json.dumps(response_errors)

            raise HTTPUnprocessableEntity(content_type=ApplicationJSON, text=response_errors_body)

        return values
