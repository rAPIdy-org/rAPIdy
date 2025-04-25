from __future__ import annotations

from concurrent.futures import Executor
from functools import wraps
from http import HTTPStatus
from typing import Any, Callable, cast, NamedTuple, overload, Type, TypeVar
from urllib.request import Request

from aiohttp.web_middlewares import (
    middleware as aiohttp_middleware,
    normalize_path_middleware,
)

from rapidy.constants import DEFAULT_JSON_ENCODER
from rapidy.encoders import CustomEncoder, Exclude, Include
from rapidy.enums import Charset, ContentType
from rapidy.typedefs import CallNext, JSONEncoder, Middleware, Unset, UnsetType

__all__ = (
    'middleware',
    'normalize_path_middleware',
)


TMiddleware = TypeVar('TMiddleware', bound=Middleware)


class MiddlewareAttrData(NamedTuple):
    """A class that holds attributes for middleware configuration.

    Attributes:
        status_code (int): The default status code to be used for the response.
        response_validate (bool): Whether the handler response should be validated.
        response_type (Union[Type[Any], None, UnsetType]): The handler response type.
        response_content_type (Union[str, ContentType, None]): The Content-Type header.
        response_charset (Union[str, Charset]): The charset for encoding and decoding response.
        response_zlib_executor (Optional[Executor]): Executor for zlib compression.
        response_zlib_executor_size (Optional[int]): Size to trigger zlib compression.
        response_include_fields (Optional[Include]): Fields to include for Pydantic models.
        response_exclude_fields (Optional[Exclude]): Fields to exclude for Pydantic models.
        response_by_alias (bool): Whether to use alias names in the response.
        response_exclude_unset (bool): Whether to exclude unset fields in the response.
        response_exclude_defaults (bool): Whether to exclude default fields in the response.
        response_exclude_none (bool): Whether to exclude fields with None values in the response.
        response_custom_encoder (Optional[CustomEncoder]): Custom encoder for Pydantic models.
        response_json_encoder (JSONEncoder): JSON encoder callable for the response.
    """

    status_code: int | HTTPStatus
    response_validate: bool
    response_type: Type[Any] | None | UnsetType
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


@overload
def middleware(middleware: TMiddleware) -> TMiddleware: ...


@overload
def middleware(
    *,
    status_code: int | HTTPStatus = HTTPStatus.OK,
    response_validate: bool = True,
    response_type: Type[Any] | None | UnsetType = Unset,  # type: ignore[has-type]
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
) -> Callable[[Any], TMiddleware]: ...


def middleware(
    middleware: TMiddleware | None = None,
    *,
    status_code: int | HTTPStatus = HTTPStatus.OK,
    response_validate: bool = True,
    response_type: Type[Any] | None | UnsetType = Unset,  # type: ignore[has-type]
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
) -> TMiddleware | Callable[[Any], TMiddleware]:
    """Create a `rapidy` middleware decorator.

    This function allows the creation of a middleware in the `rapidy` framework with various customizable options
    like response validation, content type handling, and more.

    Args:
        middleware (Optional[TMiddleware], optional): A middleware function to wrap. Defaults to None.
        status_code (int): The default status code to be used for the response.
        response_validate (bool, optional): Whether the handler's response should be validated. Defaults to True.
        response_type (Union[Type[Any], None, UnsetType], optional): The handler response type. Defaults to Unset.
        response_content_type (Union[str, ContentType, None], optional): Defines the `Content-Type` header.
                                                                         Defaults to None.
        response_charset (Union[str, Charset], optional): Charset for encoding/decoding response data.
                                                          Defaults to Charset.utf8.
        response_zlib_executor (Optional[Executor], optional): Executor to handle zlib compression. Defaults to None.
        response_zlib_executor_size (Optional[int], optional): Size in bytes for triggering zlib compression.
                                                               Defaults to None.
        response_include_fields (Optional[Include], optional): Pydantic's `include` fields parameter. Defaults to None.
        response_exclude_fields (Optional[Exclude], optional): Pydantic's `exclude` fields parameter. Defaults to None.
        response_by_alias (bool, optional): Whether to use alias names for model fields in the response.
                                            Defaults to True.
        response_exclude_unset (bool, optional): Whether to exclude unset fields. Defaults to False.
        response_exclude_defaults (bool, optional): Whether to exclude default values from the response.
                                                    Defaults to False.
        response_exclude_none (bool, optional): Whether to exclude `None` values from the response. Defaults to False.
        response_custom_encoder (Optional[CustomEncoder], optional): Custom encoder for Pydantic models.
                                                                     Defaults to None.
        response_json_encoder (JSONEncoder, optional): A callable JSON encoder function.
                                                       Defaults to DEFAULT_JSON_ENCODER.

    Returns:
        Union[TMiddleware, Callable[[Any], TMiddleware]]: A middleware function or a decorator based on input.
    """
    middleware_attr_data = MiddlewareAttrData(
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
    )

    if not middleware:

        def inner_middleware(m: TMiddleware) -> TMiddleware:
            return _create_rapidy_middleware(m, middleware_attr_data=middleware_attr_data)

        return inner_middleware

    return _create_rapidy_middleware(middleware, middleware_attr_data=middleware_attr_data)


def _create_rapidy_middleware(
    middleware: TMiddleware,
    middleware_attr_data: MiddlewareAttrData,
) -> TMiddleware:
    """Helper function to create the rapidy middleware.

    This function is used internally to generate the middleware, set attributes,
    and wrap it with the implementation.

    Args:
        middleware (TMiddleware): The middleware function to wrap.
        middleware_attr_data (MiddlewareAttrData): The configuration attributes for the middleware.

    Returns:
        TMiddleware: The wrapped middleware function.
    """
    aiohttp_middleware(middleware)
    middleware.__rapidy_middleware__ = True  # type: ignore[attr-defined]
    middleware.__attr_data__ = middleware_attr_data  # type: ignore[attr-defined]

    @wraps(middleware)
    async def impl(request: Request, handler: CallNext, **kw: Any) -> Any:
        return await middleware(request, handler, **kw)

    return cast(TMiddleware, impl)


def get_middleware_attr_data(middleware: TMiddleware) -> MiddlewareAttrData:
    """Retrieve the middleware attribute data.

    Args:
        middleware (TMiddleware): The middleware function.

    Returns:
        MiddlewareAttrData: The configuration data associated with the middleware.
    """
    return middleware.__attr_data__  # type: ignore[attr-defined]


def is_aiohttp_new_style_middleware(middleware: Middleware) -> bool:
    """Check if the middleware is using the new style for aiohttp.

    Args:
        middleware (Middleware): The middleware function.

    Returns:
        bool: True if the middleware is using the new aiohttp style, False otherwise.
    """
    return getattr(middleware, '__middleware_version__', 0) == 1


def is_rapidy_middleware(middleware: Middleware) -> bool:
    """Check if the middleware is a rapidy middleware.

    Args:
        middleware (Middleware): The middleware function.

    Returns:
        bool: True if the middleware is a rapidy middleware, False otherwise.
    """
    return getattr(middleware, '__rapidy_middleware__', False) is True
