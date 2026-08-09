from __future__ import annotations

import inspect
from collections.abc import Iterable, Sequence
from concurrent.futures import Executor
from functools import partial
from http import HTTPStatus
from typing import Any, cast, NamedTuple

from rapidy_core.encoders import CustomEncoder, Exclude, Include  # noqa: TC002 - runtime annotations
from rapidy_core.enums import Charset, ContentType  # noqa: TC002 - runtime annotations
from rapidy_core.exceptions import RapidyException

from rapidy.depends import inject_http
from rapidy.endpoint_handlers.http.controller import controller_factory
from rapidy.request import Request
from rapidy.response import Response
from rapidy.typedefs import CallNext, JSONEncoder, Middleware, UnsetType

__all__ = ('MiddlewareAttrData', 'build_onion', 'middleware_validation_wrapper', 'prepare_middlewares')


class MiddlewareAttrData(NamedTuple):
    """Response and validation policy attached by ``@middleware``."""

    status_code: int | HTTPStatus
    response_validate: bool
    response_type: type[Any] | UnsetType | None
    response_content_type: str | ContentType | None
    response_charset: str | Charset
    response_zlib_executor: Executor | None
    response_zlib_executor_size: int | None
    response_include_fields: Include | None
    response_exclude_fields: Exclude | None
    response_by_alias: bool
    response_exclude_unset: bool
    response_exclude_defaults: bool
    response_exclude_none: bool
    response_custom_encoder: CustomEncoder | None
    response_json_encoder: JSONEncoder


class MiddlewareIsNotAsyncFuncTypeError(RapidyException):
    """Raised when application startup receives a synchronous middleware."""

    message = 'Middleware must be an async function. Current type: `{type_middleware}`'


def build_onion(middlewares: Sequence[Middleware], terminal: CallNext) -> CallNext:
    """Fold one middleware sequence once; runtime calls reuse the returned chain."""
    call_next = terminal
    for current_middleware in reversed(middlewares):
        call_next = cast('CallNext', partial(cast('Any', current_middleware), call_next=call_next))
    return call_next


def prepare_middlewares(middlewares: Iterable[Middleware]) -> tuple[Middleware, ...]:
    """Validate middleware callables and attach rAPIdy extraction/response policy."""
    from rapidy.middlewares import get_middleware_attr_data, is_rapidy_middleware  # noqa: PLC0415

    prepared: list[Middleware] = []
    for current_middleware in middlewares:
        is_async = inspect.iscoroutinefunction(current_middleware) or inspect.iscoroutinefunction(
            type(current_middleware).__call__
        )
        if not is_async:
            raise MiddlewareIsNotAsyncFuncTypeError(type_middleware=str(type(current_middleware)))
        prepared_middleware = current_middleware
        if is_rapidy_middleware(current_middleware):
            prepared_middleware = middleware_validation_wrapper(
                current_middleware,
                **get_middleware_attr_data(current_middleware)._asdict(),
            )
        prepared.append(prepared_middleware)
    return tuple(prepared)


def middleware_validation_wrapper(
    middleware: Middleware,
    *,
    status_code: int | HTTPStatus,
    response_validate: bool,
    response_type: type[Any] | UnsetType | None,
    response_content_type: str | ContentType | None,
    response_charset: str | Charset,
    response_zlib_executor: Executor | None,
    response_zlib_executor_size: int | None,
    response_json_encoder: JSONEncoder,
    response_include_fields: Include | None,
    response_exclude_fields: Exclude | None,
    response_by_alias: bool,
    response_exclude_unset: bool,
    response_exclude_defaults: bool,
    response_exclude_none: bool,
    response_custom_encoder: CustomEncoder | None,
) -> Middleware:
    """Apply request extraction, DI, and response policy to a marked middleware."""
    from rapidy.middlewares import middleware as middleware_decorator  # noqa: PLC0415

    injected_middleware = inject_http(middleware)
    handler_controller = controller_factory(
        injected_middleware,
        status_code=status_code,
        response_validate=response_validate,
        response_type=response_type,
        response_content_type=response_content_type,
        response_charset=str(response_charset),
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
    )

    @middleware_decorator
    async def inner(request: Request, call_next: CallNext) -> Response:
        pre_response: Response | None = None
        validated_data = await handler_controller.validate_request(request=request)
        if handler_controller.response_attribute_name:
            pre_response = Response(
                status=int(status_code),
                content_type=response_content_type,
                charset=response_charset,
                zlib_executor=response_zlib_executor,
                zlib_executor_size=response_zlib_executor_size,
                include=response_include_fields,
                exclude=response_exclude_fields,
                by_alias=response_by_alias,
                exclude_unset=response_exclude_unset,
                exclude_defaults=response_exclude_defaults,
                exclude_none=response_exclude_none,
                custom_encoder=response_custom_encoder,
                json_encoder=response_json_encoder,
            )
            validated_data[handler_controller.response_attribute_name] = pre_response

        handler_result = await injected_middleware(request, call_next, **validated_data)
        return cast('Response', await handler_controller.create_response(handler_result, pre_response))

    return inner
