from concurrent.futures import Executor
from typing import Any, Callable, NamedTuple, Optional, overload, Type, TypeVar, Union

from aiohttp.helpers import sentinel
from aiohttp.typedefs import DEFAULT_JSON_ENCODER, JSONEncoder
from aiohttp.web_middlewares import middleware as aiohttp_middleware, normalize_path_middleware

from rapidy.encoders import CustomEncoder, Exclude, Include
from rapidy.enums import Charset, ContentType
from rapidy.typedefs import Middleware

__all__ = (
    'middleware',
    'normalize_path_middleware',
)


TMiddleware = TypeVar('TMiddleware')


class MiddlewareAttrData(NamedTuple):
    response_validate: bool
    response_type: Union[Type[Any], None]
    response_content_type: Union[str, ContentType, None]
    response_charset: Union[str, Charset]
    response_zlib_executor: Optional[Executor]
    response_zlib_executor_size: Optional[int]
    response_include_fields: Optional[Include]
    response_exclude_fields: Optional[Exclude]
    response_by_alias: bool
    response_exclude_unset: bool
    response_exclude_defaults: bool
    response_exclude_none: bool
    response_custom_encoder: Optional[CustomEncoder]
    response_json_encoder: JSONEncoder


@overload
def middleware(middleware: TMiddleware) -> TMiddleware:  # noqa: WPS442
    ...  # noqa: WPS428


@overload
def middleware(
        *,
        response_validate: bool = True,
        response_type: Union[Type[Any], None] = sentinel,
        response_content_type: Union[str, ContentType, None] = None,
        response_charset: Union[str, Charset] = Charset.utf8,
        response_zlib_executor: Optional[Executor] = None,
        response_zlib_executor_size: Optional[int] = None,
        response_include_fields: Optional[Include] = None,
        response_exclude_fields: Optional[Exclude] = None,
        response_by_alias: bool = True,
        response_exclude_unset: bool = False,
        response_exclude_defaults: bool = False,
        response_exclude_none: bool = False,
        response_custom_encoder: Optional[CustomEncoder] = None,
        response_json_encoder: JSONEncoder = DEFAULT_JSON_ENCODER,
) -> Callable[[Any], TMiddleware]:
    ...  # noqa: WPS428


def middleware(
        middleware: Optional[TMiddleware] = None,  # noqa: WPS442
        *,
        response_validate: bool = True,
        response_type: Union[Type[Any], None] = sentinel,
        response_content_type: Union[str, ContentType, None] = None,
        response_charset: Union[str, Charset] = Charset.utf8,
        response_zlib_executor: Optional[Executor] = None,
        response_zlib_executor_size: Optional[int] = None,
        response_include_fields: Optional[Include] = None,
        response_exclude_fields: Optional[Exclude] = None,
        response_by_alias: bool = True,
        response_exclude_unset: bool = False,
        response_exclude_defaults: bool = False,
        response_exclude_none: bool = False,
        response_custom_encoder: Optional[CustomEncoder] = None,
        response_json_encoder: JSONEncoder = DEFAULT_JSON_ENCODER,
) -> Union[TMiddleware, Callable[[Any], TMiddleware]]:
    """rAPIdy middleware decorator.

    Args:
        middleware:
            Function to wrap.
        response_validate:
            Flag determines whether the handler response should be validated.
        response_type:
            Handler response type.
            This attribute is used to create the response model.
            If this attribute is defined, it overrides the handler return annotation logic.
        response_content_type:
            Attribute defines the `Content-Type` header and performs post-processing of the endpoint handler return.
        response_charset:
            The `charset` that will be used to encode and decode handler result data.
        response_zlib_executor:
            Executor to use for zlib compression
        response_zlib_executor_size:
            Length in bytes which will trigger zlib compression of body to happen in an executor
        response_include_fields:
            Pydantic's `include` parameter, passed to Pydantic models to set the fields to include.
        response_exclude_fields:
            Pydantic's `exclude` parameter, passed to Pydantic models to set the fields to exclude.
        response_by_alias:
            Pydantic's `by_alias` parameter, passed to Pydantic models to define
            if the output should use the alias names (when provided) or the Python
            attribute names. In an API, if you set an alias, it's probably because you
            want to use it in the result, so you probably want to leave this set to `True`.
        response_exclude_unset:
            Pydantic's `exclude_unset` parameter, passed to Pydantic models to define
            if it should exclude from the output the fields that were not explicitly
            set (and that only had their default values).
        response_exclude_defaults:
            Pydantic's `exclude_defaults` parameter, passed to Pydantic models to define
            if it should exclude from the output the fields that had the same default
            value, even when they were explicitly set.
        response_exclude_none:
            Pydantic's `exclude_none` parameter, passed to Pydantic models to define
            if it should exclude from the output any fields that have a `None` value.
        response_custom_encoder:
            Pydantic's `custom_encoder` parameter, passed to Pydantic models to define a custom encoder.
        response_json_encoder:
            Any callable that accepts an object and returns a JSON string.
            Will be used if dumps=True
    """
    middleware_attr_data = MiddlewareAttrData(
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
    )

    if not middleware:
        def inner_middleware(m: TMiddleware) -> TMiddleware:  # noqa: WPS440 WPS442
            return _create_rapidy_middleware(m, middleware_attr_data=middleware_attr_data)
        return inner_middleware

    return _create_rapidy_middleware(middleware, middleware_attr_data=middleware_attr_data)


def _create_rapidy_middleware(
        middleware: TMiddleware,  # noqa: WPS440 WPS442
        middleware_attr_data: MiddlewareAttrData,
) -> TMiddleware:
    aiohttp_middleware(middleware)
    middleware.__rapidy_middleware__ = True  # type: ignore[attr-defined]
    middleware.__attr_data__ = middleware_attr_data  # type: ignore[arg-type, attr-defined, unused-ignore]
    return middleware


def get_middleware_attr_data(middleware: TMiddleware) -> MiddlewareAttrData:  # noqa: WPS442
    return middleware.__attr_data__  # type: ignore[attr-defined]


def is_aiohttp_new_style_middleware(middleware: Middleware) -> bool:  # noqa: WPS442
    return getattr(middleware, '__middleware_version__', 0) == 1


def is_rapidy_middleware(middleware: Middleware) -> bool:  # noqa: WPS442
    return getattr(middleware, '__rapidy_middleware__', False) is True
