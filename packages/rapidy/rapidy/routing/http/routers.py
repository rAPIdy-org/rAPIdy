from __future__ import annotations

import inspect
from abc import ABC
from concurrent.futures import Executor
from functools import wraps
from http import HTTPStatus
from typing import Any, cast, TYPE_CHECKING

from rapidy_core.constants import DEFAULT_JSON_ENCODER
from rapidy_core.enums import Charset, ContentType, HTTPMethod

from rapidy._base_exceptions import RapidyException, RapidyHandlerException
from rapidy.response import Response
from rapidy.routing.http.base import BaseHTTPRouter
from rapidy.typedefs import (
    ControllerHTTPRouterType,
    Handler,
    JSONEncoder,
    TerminalHandler,
    Unset,
    UnsetType,
)

if TYPE_CHECKING:
    from rapidy_core.encoders import CustomEncoder, Exclude, Include

    from rapidy.application import Rapidy
    from rapidy.request import Request

__all__ = ('get', 'post', 'put', 'patch', 'delete', 'head', 'options')

# TODO(08-middleware-mounts): add HTTPRouter to __all__.  # noqa: FIX002
# TODO(10-response-contract): add controller to __all__.  # noqa: FIX002

MethodName = HTTPMethod
DUNDER_NAME_MIN_LENGTH = 4


def is_dunder_name(name: str) -> bool:
    """Return whether a name has the canonical dunder form."""
    return (
        len(name) > DUNDER_NAME_MIN_LENGTH
        and name[:2] == name[-2:] == '__'
        and name[2] != '_'
        and name[-3] != '_'
    )


class MissingPathError(RapidyHandlerException):
    """Raised when a decorated handler has no path."""

    message = 'Handler must contain `path` attribute.'


class HandlerIsNotAsyncFuncTypeError(RapidyException):
    """Raised when a method decorator receives a synchronous handler."""

    message = 'Handler must be an async function. Current type: `{type_handler}`'


def _is_async_callable(handler: Handler) -> bool:
    return inspect.iscoroutinefunction(handler) or inspect.iscoroutinefunction(type(handler).__call__)


def _build_terminal(handler: Handler, route_kwargs: dict[str, Any]) -> TerminalHandler:
    parameters = inspect.signature(handler).parameters

    @wraps(handler)
    async def terminal(request: Request) -> Response:
        if not parameters:
            result = await handler()
        elif len(parameters) == 1:
            result = await handler(request)
        else:
            msg = 'Milestone 03 handlers accept zero arguments or one Request argument'
            raise TypeError(msg)

        if isinstance(result, Response):
            return result
        status = int(route_kwargs.get('status_code', HTTPStatus.OK))
        return Response(result, status=status)

    # TODO(10-response-contract): apply all response_* route kwargs in the controller.  # noqa: FIX002
    return terminal


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

        route_kwargs = dict(self._route_kwargs)
        allow_head = bool(route_kwargs.pop('allow_head', True))
        terminal = _build_terminal(self._handler, route_kwargs)
        application._matcher.add_route(  # noqa: SLF001
            self._method_name.value,
            self.path,
            terminal,
            route_kwargs,
            allow_head=allow_head,
        )


class HTTPMethodRouteHandler(HTTPRouteHandler):
    """Decorator restricted to asynchronous endpoint callables."""

    def __call__(self, handler: Handler) -> HTTPRouteHandler:
        if _is_async_callable(handler):
            return super().__call__(handler)
        raise HandlerIsNotAsyncFuncTypeError(type_handler=str(type(handler)))


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
