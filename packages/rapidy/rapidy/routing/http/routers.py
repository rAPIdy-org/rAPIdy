from __future__ import annotations

import inspect
from abc import ABC
from collections.abc import Iterable
from concurrent.futures import Executor
from http import HTTPStatus
from typing import Any, cast, NamedTuple, TYPE_CHECKING

from rapidy_core.annotation_checkers import lenient_issubclass
from rapidy_core.constants import DEFAULT_JSON_ENCODER
from rapidy_core.enums import Charset, ContentType, HTTPMethod, HTTPRequestParamType

from rapidy._base_exceptions import RapidyException, RapidyHandlerException
from rapidy.constants import CLIENT_MAX_SIZE
from rapidy.depends import inject_http
from rapidy.endpoint_handlers.http.attrs_extractor import get_http_handler_info
from rapidy.endpoint_handlers.http.handlers import handler_validation_wrapper, METH_ALL, view_validation_wrapper
from rapidy.routing.http.base import BaseHTTPRouter
from rapidy.routing.http.helper_types import HandlerPartial
from rapidy.routing.matcher import RouteRecord
from rapidy.typedefs import (
    ControllerHTTPRouterType,
    Handler,
    JSONEncoder,
    LifespanCTX,
    LifespanHook,
    Middleware,
    Unset,
    UnsetType,
    View,
)

if TYPE_CHECKING:
    from rapidy_core.encoders import CustomEncoder, Exclude, Include
    from rapidy_core.parameters.http import RequestParamFieldInfo

    from rapidy.application import Rapidy

__all__ = (
    'HandlerParameterRecord',
    'HTTPRouter',
    'RouteParameter',
    'get_route_parameters',
    'get',
    'post',
    'put',
    'patch',
    'delete',
    'head',
    'options',
    'controller',
)

MethodName = HTTPMethod
DUNDER_NAME_MIN_LENGTH = 4


class HandlerParameterRecord(NamedTuple):
    """Immutable OpenAPI-ready request parameter metadata captured at registration."""

    name: str
    annotation: Any
    param_type: HTTPRequestParamType
    alias: str | None
    required: bool
    default: Any
    extract_single: bool
    field_info: RequestParamFieldInfo

    @property
    def source(self) -> HTTPRequestParamType:
        """Expose the parameter source under the terminology used by OpenAPI consumers."""
        return self.param_type


RouteParameter = HandlerParameterRecord


def _get_handler_parameters(handler: Handler) -> tuple[HandlerParameterRecord, ...]:
    handler_info = get_http_handler_info(handler, request_attr_can_declare_fst=True)
    return tuple(
        HandlerParameterRecord(
            name=attr.attribute_name,
            annotation=attr.field_info.annotation,
            param_type=attr.http_param_type,
            alias=attr.field_info.alias,
            required=attr.field_info.is_required(),
            default=attr.field_info.default,
            extract_single=attr.extract_as_single_param,
            field_info=attr.field_info,
        )
        for attr in handler_info.request_params
    )


def get_route_parameters(route: RouteRecord) -> tuple[HandlerParameterRecord, ...]:
    """Return the immutable registration-time parameter snapshot for a route."""
    return cast('tuple[HandlerParameterRecord, ...]', route.parameters)


def is_dunder_name(name: str) -> bool:
    """Return whether a name has the canonical dunder form."""
    return len(name) > DUNDER_NAME_MIN_LENGTH and name[:2] == name[-2:] == '__' and name[2] != '_' and name[-3] != '_'


class MissingPathError(RapidyHandlerException):
    """Raised when a decorated handler has no path."""

    message = 'Handler must contain `path` attribute.'


class HandlerIsNotAsyncFuncTypeError(RapidyException):
    """Raised when a method decorator receives a synchronous handler."""

    message = 'Handler must be an async function. Current type: `{type_handler}`'


def is_controller(handler: Any) -> bool:
    """Return whether a router object is a class controller decorator."""
    return isinstance(handler, controller)


def _is_async_callable(handler: Handler) -> bool:
    return inspect.iscoroutinefunction(handler) or inspect.iscoroutinefunction(type(handler).__call__)


class HTTPRouter(BaseHTTPRouter):
    """Group routes and application policy under a mounted subapplication."""

    __slots__ = ('application', 'path')

    def __init__(
        self,
        path: str,
        route_handlers: Iterable[BaseHTTPRouter | Any] = (),
        *,
        middlewares: Iterable[Middleware] | None = None,
        client_max_size: int = CLIENT_MAX_SIZE,
        lifespan: list[LifespanCTX] | None = None,
        on_startup: list[LifespanHook] | None = None,
        on_shutdown: list[LifespanHook] | None = None,
        on_cleanup: list[LifespanHook] | None = None,
    ) -> None:
        from rapidy.application import Rapidy  # noqa: PLC0415

        super().__init__(path=path)
        self.application = Rapidy(
            middlewares=middlewares,
            http_route_handlers=route_handlers,
            client_max_size=client_max_size,
            lifespan=lifespan or (),
            on_startup=on_startup or (),
            on_shutdown=on_shutdown or (),
            on_cleanup=on_cleanup or (),
        )

    def route_register(self, application: Rapidy) -> None:
        application.add_subapp(prefix=cast('str', self.path), subapp=self.application)


class HTTPRouteHandler(BaseHTTPRouter, ABC):
    """Base object shared by all HTTP method decorators."""

    _method_name: MethodName
    _set_route_kwargs: dict[str, Any]
    _route_kwargs: dict[str, Any]
    _handler: Handler

    def __init__(
        self,
        path: str | None = None,
        *,
        status_code: int | HTTPStatus | UnsetType = Unset,
        response_validate: bool | UnsetType = Unset,
        response_type: type[Any] | UnsetType | None = Unset,
        response_content_type: str | ContentType | UnsetType | None = Unset,
        response_charset: str | Charset | UnsetType = Unset,
        response_zlib_executor: Executor | UnsetType | None = Unset,
        response_zlib_executor_size: int | UnsetType | None = Unset,
        response_include_fields: Include | UnsetType | None = Unset,
        response_exclude_fields: Exclude | UnsetType | None = Unset,
        response_by_alias: bool | UnsetType = Unset,
        response_exclude_unset: bool | UnsetType = Unset,
        response_exclude_defaults: bool | UnsetType = Unset,
        response_exclude_none: bool | UnsetType = Unset,
        response_custom_encoder: CustomEncoder | UnsetType | None = Unset,
        response_json_encoder: JSONEncoder | UnsetType = Unset,
        **kwargs: Any,
    ) -> None:
        raw_kwargs = {
            'status_code': status_code,
            'response_validate': response_validate,
            'response_type': response_type,
            'response_content_type': response_content_type,
            'response_charset': response_charset,
            'response_zlib_executor': response_zlib_executor,
            'response_zlib_executor_size': response_zlib_executor_size,
            'response_include_fields': response_include_fields,
            'response_exclude_fields': response_exclude_fields,
            'response_by_alias': response_by_alias,
            'response_exclude_unset': response_exclude_unset,
            'response_exclude_defaults': response_exclude_defaults,
            'response_exclude_none': response_exclude_none,
            'response_custom_encoder': response_custom_encoder,
            'response_json_encoder': response_json_encoder,
            **kwargs,
        }
        self._set_route_kwargs = {key: value for key, value in raw_kwargs.items() if value is not Unset}
        self.init(path=path, **self._set_route_kwargs)

    def init(
        self,
        path: str | None = None,
        *,
        status_code: int | HTTPStatus = HTTPStatus.OK,
        response_validate: bool = True,
        response_type: type[Any] | UnsetType | None = Unset,
        response_content_type: str | ContentType | None = None,
        response_charset: str | Charset = Charset.utf8,
        response_zlib_executor: Executor | None = None,
        response_zlib_executor_size: int | None = None,
        response_include_fields: Include | None = None,
        response_exclude_fields: Exclude | None = None,
        response_by_alias: bool = True,
        response_exclude_unset: bool = False,
        response_exclude_defaults: bool = False,
        response_exclude_none: bool = False,
        response_custom_encoder: CustomEncoder | None = None,
        response_json_encoder: JSONEncoder = DEFAULT_JSON_ENCODER,
        **kwargs: Any,
    ) -> None:
        self._route_kwargs = {
            'status_code': status_code,
            'response_validate': response_validate,
            'response_type': response_type,
            'response_content_type': response_content_type,
            'response_charset': response_charset,
            'response_zlib_executor': response_zlib_executor,
            'response_zlib_executor_size': response_zlib_executor_size,
            'response_include_fields': response_include_fields,
            'response_exclude_fields': response_exclude_fields,
            'response_by_alias': response_by_alias,
            'response_exclude_unset': response_exclude_unset,
            'response_exclude_defaults': response_exclude_defaults,
            'response_exclude_none': response_exclude_none,
            'response_custom_encoder': response_custom_encoder,
            'response_json_encoder': response_json_encoder,
            **kwargs,
        }
        super().__init__(path=path)

    def __call__(self, handler: Handler) -> HTTPRouteHandler:
        self._handler = handler
        return self

    @classmethod
    def reg(
        cls,
        path: str,
        handler: Handler | ControllerHTTPRouterType,
        *,
        status_code: int | HTTPStatus | UnsetType = Unset,
        response_validate: bool | UnsetType = Unset,
        response_type: type[Any] | UnsetType | None = Unset,
        response_content_type: str | ContentType | UnsetType | None = Unset,
        response_charset: str | Charset | UnsetType = Unset,
        response_zlib_executor: Executor | UnsetType | None = Unset,
        response_zlib_executor_size: int | UnsetType | None = Unset,
        response_include_fields: Include | UnsetType | None = Unset,
        response_exclude_fields: Exclude | UnsetType | None = Unset,
        response_by_alias: bool | UnsetType = Unset,
        response_exclude_unset: bool | UnsetType = Unset,
        response_exclude_defaults: bool | UnsetType = Unset,
        response_exclude_none: bool | UnsetType = Unset,
        response_custom_encoder: CustomEncoder | UnsetType | None = Unset,
        response_json_encoder: JSONEncoder | UnsetType = Unset,
        **kwargs: Any,
    ) -> HTTPRouteHandler:
        route = cls(
            path=path,
            status_code=status_code,
            response_validate=response_validate,
            response_type=response_type,
            response_content_type=response_content_type,
            response_charset=response_charset,
            response_zlib_executor=response_zlib_executor,
            response_zlib_executor_size=response_zlib_executor_size,
            response_include_fields=response_include_fields,
            response_exclude_fields=response_exclude_fields,
            response_by_alias=response_by_alias,
            response_exclude_unset=response_exclude_unset,
            response_exclude_defaults=response_exclude_defaults,
            response_exclude_none=response_exclude_none,
            response_custom_encoder=response_custom_encoder,
            response_json_encoder=response_json_encoder,
            **kwargs,
        )
        return route(cast('Handler', handler))

    def route_register(self, application: Rapidy) -> None:
        if self.path is None:
            raise MissingPathError.create(handler=self._handler)

        if lenient_issubclass(self._handler, View):
            view = cast('type[View]', self._handler)
            route_kwargs = dict(self._route_kwargs)
            route_kwargs.pop('allow_head', None)
            view_terminal = view_validation_wrapper(view, method=MethodName.any, **route_kwargs)
            methods = {name.upper() for name in dir(view) if name.upper() in METH_ALL}
            if 'GET' in methods:
                methods.add('HEAD')
            for method_name in ('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'):
                if method_name not in methods:
                    continue
                method_handler = cast('Handler', getattr(view, method_name.lower()))
                application._matcher.add_route(  # noqa: SLF001
                    method_name,
                    self.path,
                    view_terminal,
                    route_kwargs,
                    allow_head=False,
                    handler=method_handler,
                    parameters=_get_handler_parameters(method_handler),
                )
            return

        if is_controller(self):
            controller_instance = self._handler()
            for handler_attr_name in dir(controller_instance):
                if is_dunder_name(handler_attr_name):
                    continue
                handler_attr = getattr(controller_instance, handler_attr_name)
                if not isinstance(handler_attr, HTTPRouteHandler):
                    continue
                handler_with_di = inject_http(handler_attr._handler)  # noqa: SLF001
                handler_attr._handler = HandlerPartial(  # noqa: SLF001
                    controller_instance=controller_instance,
                    handler=handler_with_di,
                )
                handler_attr.path = self._create_sub_route_path(sub_path=handler_attr.path)
                handler_attr._route_kwargs = self._extend_kw(  # noqa: SLF001
                    sub_route_kwargs=handler_attr._route_kwargs,  # noqa: SLF001
                    sub_route_set_kwargs=handler_attr._set_route_kwargs,  # noqa: SLF001
                )
                handler_attr.route_register(application)
            return

        route_kwargs = dict(self._route_kwargs)
        allow_head = bool(route_kwargs.pop('allow_head', True))
        terminal = handler_validation_wrapper(self._handler, **route_kwargs)
        parameters = _get_handler_parameters(self._handler)
        application._matcher.add_route(  # noqa: SLF001
            self._method_name.value,
            self.path,
            terminal,
            route_kwargs,
            allow_head=allow_head,
            handler=self._handler,
            parameters=parameters,
        )

    def _create_sub_route_path(self, sub_path: str | None) -> str:
        if sub_path is None:
            return cast('str', self.path)
        return f'{self.path}{sub_path}'

    def _extend_kw(
        self,
        sub_route_kwargs: dict[str, Any],
        sub_route_set_kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            **sub_route_kwargs,
            **self._set_route_kwargs,
            **sub_route_set_kwargs,
        }


class HTTPMethodRouteHandler(HTTPRouteHandler):
    """Decorator restricted to asynchronous endpoint callables."""

    def __call__(self, handler: Handler) -> HTTPRouteHandler:
        if _is_async_callable(handler):
            return super().__call__(handler)
        raise HandlerIsNotAsyncFuncTypeError(type_handler=str(type(handler)))


class controller(HTTPRouteHandler):
    """Register a class whose decorated methods form related routes."""

    _method_name = MethodName.any

    def __init__(
        self,
        path: str,
        *,
        status_code: int | HTTPStatus | UnsetType = Unset,
        response_validate: bool | UnsetType = Unset,
        response_type: type[Any] | UnsetType | None = Unset,
        response_content_type: str | ContentType | UnsetType | None = Unset,
        response_charset: str | Charset | UnsetType = Unset,
        response_zlib_executor: Executor | UnsetType | None = Unset,
        response_zlib_executor_size: int | UnsetType | None = Unset,
        response_include_fields: Include | UnsetType | None = Unset,
        response_exclude_fields: Exclude | UnsetType | None = Unset,
        response_by_alias: bool | UnsetType = Unset,
        response_exclude_unset: bool | UnsetType = Unset,
        response_exclude_defaults: bool | UnsetType = Unset,
        response_exclude_none: bool | UnsetType = Unset,
        response_custom_encoder: CustomEncoder | UnsetType | None = Unset,
        response_json_encoder: JSONEncoder | UnsetType = Unset,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            path=path,
            status_code=status_code,
            response_validate=response_validate,
            response_type=response_type,
            response_content_type=response_content_type,
            response_charset=response_charset,
            response_zlib_executor=response_zlib_executor,
            response_zlib_executor_size=response_zlib_executor_size,
            response_include_fields=response_include_fields,
            response_exclude_fields=response_exclude_fields,
            response_by_alias=response_by_alias,
            response_exclude_unset=response_exclude_unset,
            response_exclude_defaults=response_exclude_defaults,
            response_exclude_none=response_exclude_none,
            response_custom_encoder=response_custom_encoder,
            response_json_encoder=response_json_encoder,
            **kwargs,
        )


class get(HTTPMethodRouteHandler):
    """Register a GET route and, by default, its automatic HEAD route."""

    _method_name = MethodName.get

    def __init__(
        self,
        path: str | None = None,
        *,
        allow_head: bool = True,
        status_code: int | HTTPStatus | UnsetType = Unset,
        response_validate: bool | UnsetType = Unset,
        response_type: type[Any] | UnsetType | None = Unset,
        response_content_type: str | ContentType | UnsetType | None = Unset,
        response_charset: str | Charset | UnsetType = Unset,
        response_zlib_executor: Executor | UnsetType | None = Unset,
        response_zlib_executor_size: int | UnsetType | None = Unset,
        response_include_fields: Include | UnsetType | None = Unset,
        response_exclude_fields: Exclude | UnsetType | None = Unset,
        response_by_alias: bool | UnsetType = Unset,
        response_exclude_unset: bool | UnsetType = Unset,
        response_exclude_defaults: bool | UnsetType = Unset,
        response_exclude_none: bool | UnsetType = Unset,
        response_custom_encoder: CustomEncoder | UnsetType | None = Unset,
        response_json_encoder: JSONEncoder | UnsetType = Unset,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            path=path,
            allow_head=allow_head,
            status_code=status_code,
            response_validate=response_validate,
            response_type=response_type,
            response_content_type=response_content_type,
            response_charset=response_charset,
            response_zlib_executor=response_zlib_executor,
            response_zlib_executor_size=response_zlib_executor_size,
            response_include_fields=response_include_fields,
            response_exclude_fields=response_exclude_fields,
            response_by_alias=response_by_alias,
            response_exclude_unset=response_exclude_unset,
            response_exclude_defaults=response_exclude_defaults,
            response_exclude_none=response_exclude_none,
            response_custom_encoder=response_custom_encoder,
            response_json_encoder=response_json_encoder,
            **kwargs,
        )


class post(HTTPMethodRouteHandler):
    """Register a POST route."""

    _method_name = MethodName.post


class put(HTTPMethodRouteHandler):
    """Register a PUT route."""

    _method_name = MethodName.put


class patch(HTTPMethodRouteHandler):
    """Register a PATCH route."""

    _method_name = MethodName.patch


class delete(HTTPMethodRouteHandler):
    """Register a DELETE route."""

    _method_name = MethodName.delete


class head(HTTPMethodRouteHandler):
    """Register an explicit HEAD route."""

    _method_name = MethodName.head


class options(HTTPMethodRouteHandler):
    """Register an explicit OPTIONS route."""

    _method_name = MethodName.options
