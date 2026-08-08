from __future__ import annotations

from concurrent.futures import Executor
from http import HTTPStatus
from typing import Any, Type, TYPE_CHECKING

from aiohttp.hdrs import METH_ANY, METH_DELETE, METH_GET, METH_HEAD, METH_OPTIONS, METH_PATCH, METH_POST, METH_PUT
from aiohttp.typedefs import DEFAULT_JSON_ENCODER, JSONEncoder, PathLike
from aiohttp.web_routedef import (
    AbstractRouteDef,
    RouteDef,
    RouteTableDef as AioHTTPRouteTableDef,
    StaticDef,
)

from rapidy.encoders import CustomEncoder, Exclude, Include
from rapidy.enums import Charset, ContentType
from rapidy.typedefs import HandlerOrView, RouterDeco, Unset, UnsetType

if TYPE_CHECKING:
    from aiohttp.abc import AbstractView

__all__ = (
    'AbstractRouteDef',
    'RouteDef',
    'StaticDef',
    'RouteTableDef',
    'get',
    'post',
    'patch',
    'put',
    'delete',
    'view',
    'options',
    'head',
    'static',
    'route',
)


def route(method: str, path: str, handler: HandlerOrView, **kwargs: Any) -> RouteDef:
    """Creates a new RouteDef item for registering a web handler.

    Args:
        method (str): The HTTP method for the route (e.g., 'GET', 'POST').
        path (str): The resource path specification for the route.
        handler (HandlerOrView): The handler function or view associated with the route.
        kwargs (Any): Additional internal arguments to configure the route.

    Returns:
        RouteDef: The route definition object.
    """
    return RouteDef(method=method, path=path, handler=handler, kwargs=kwargs)


def get(
    path: str,
    handler: HandlerOrView,
    *,
    name: str | None = None,
    allow_head: bool = True,
    status_code: int | HTTPStatus = HTTPStatus.OK,
    response_validate: bool = True,
    response_type: Type[Any] | None | UnsetType = Unset,
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
) -> RouteDef:
    """Creates a new RouteDef item for registering a GET web handler.

    Args:
        path (str): The resource path specification for the route.
        handler (HandlerOrView): The handler function or view for the route.
        name (Optional[str]): Optional resource name.
        allow_head (bool): If True (default), allows a HEAD route with the same handler as GET.
        status_code (int): The default status code to be used for the response.
        response_validate (bool): Determines whether the handler's response should be validated.
        response_type (Union[Type[Any], None, UnsetType]): The type of response expected.
        response_content_type (Union[str, ContentType, None]): Defines the `Content-Type` header for the response.
        response_charset (Union[str, Charset]): Charset used for encoding and decoding the response.
        response_zlib_executor (Optional[Executor]): Executor for zlib compression.
        response_zlib_executor_size (Optional[int]): The size threshold for triggering zlib compression.
        response_include_fields (Optional[Include]): Fields to include during Pydantic model serialization.
        response_exclude_fields (Optional[Exclude]): Fields to exclude during Pydantic model serialization.
        response_by_alias (bool): Whether to use aliases for fields during serialization.
        response_exclude_unset (bool): Whether to exclude unset fields from the response.
        response_exclude_defaults (bool): Whether to exclude fields with default values from the response.
        response_exclude_none (bool): Whether to exclude fields with `None` values from the response.
        response_custom_encoder (Optional[CustomEncoder]): A custom encoder for Pydantic models.
        response_json_encoder (JSONEncoder): Custom JSON encoder function for serializing the response.
        kwargs (Any): Additional internal arguments for the route.

    Returns:
        RouteDef: The route definition object for the GET request.
    """
    return route(
        method=METH_GET,
        path=path,
        handler=handler,
        name=name,
        allow_head=allow_head,
        **kwargs,
        # rapidy attrs
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


def post(
    path: str,
    handler: HandlerOrView,
    *,
    name: str | None = None,
    status_code: int | HTTPStatus = HTTPStatus.OK,
    response_validate: bool = True,
    response_type: Type[Any] | None | UnsetType = Unset,
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
) -> RouteDef:
    """Creates a new RouteDef item for registering a POST web handler.

    Args:
        path (str): The resource path specification for the route.
        handler (HandlerOrView): The handler function or view for the route.
        name (Optional[str]): Optional resource name.
        status_code (int): The default status code to be used for the response.
        response_validate (bool): Determines whether the handler's response should be validated.
        response_type (Union[Type[Any], None, UnsetType]): The type of response expected.
        response_content_type (Union[str, ContentType, None]): Defines the `Content-Type` header for the response.
        response_charset (Union[str, Charset]): Charset used for encoding and decoding the response.
        response_zlib_executor (Optional[Executor]): Executor for zlib compression.
        response_zlib_executor_size (Optional[int]): The size threshold for triggering zlib compression.
        response_include_fields (Optional[Include]): Fields to include during Pydantic model serialization.
        response_exclude_fields (Optional[Exclude]): Fields to exclude during Pydantic model serialization.
        response_by_alias (bool): Whether to use aliases for fields during serialization.
        response_exclude_unset (bool): Whether to exclude unset fields from the response.
        response_exclude_defaults (bool): Whether to exclude fields with default values from the response.
        response_exclude_none (bool): Whether to exclude fields with `None` values from the response.
        response_custom_encoder (Optional[CustomEncoder]): A custom encoder for Pydantic models.
        response_json_encoder (JSONEncoder): Custom JSON encoder function for serializing the response.
        kwargs (Any): Additional internal arguments for the route.

    Returns:
        RouteDef: The route definition object for the POST request.
    """
    return route(
        # aiohttp attrs
        method=METH_POST,
        path=path,
        handler=handler,
        name=name,
        **kwargs,
        # rapidy attrs
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


def put(
    path: str,
    handler: HandlerOrView,
    *,
    name: str | None = None,
    status_code: int | HTTPStatus = HTTPStatus.OK,
    response_validate: bool = True,
    response_type: Type[Any] | None | UnsetType = Unset,
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
) -> RouteDef:
    """Create a new RouteDef item for registering PUT web-handler.

    Args:
        path (str): The resource path specification for the route.
        handler (HandlerOrView): The handler function or view for the route.
        name (Optional[str]): Optional resource name.
        status_code (int): The default status code to be used for the response.
        response_validate (bool): Determines whether the handler's response should be validated.
        response_type (Union[Type[Any], None, UnsetType]): The type of response expected.
        response_content_type (Union[str, ContentType, None]): Defines the `Content-Type` header for the response.
        response_charset (Union[str, Charset]): Charset used for encoding and decoding the response.
        response_zlib_executor (Optional[Executor]): Executor for zlib compression.
        response_zlib_executor_size (Optional[int]): The size threshold for triggering zlib compression.
        response_include_fields (Optional[Include]): Fields to include during Pydantic model serialization.
        response_exclude_fields (Optional[Exclude]): Fields to exclude during Pydantic model serialization.
        response_by_alias (bool): Whether to use aliases for fields during serialization.
        response_exclude_unset (bool): Whether to exclude unset fields from the response.
        response_exclude_defaults (bool): Whether to exclude fields with default values from the response.
        response_exclude_none (bool): Whether to exclude fields with `None` values from the response.
        response_custom_encoder (Optional[CustomEncoder]): A custom encoder for Pydantic models.
        response_json_encoder (JSONEncoder): Custom JSON encoder function for serializing the response.
        kwargs (Any): Additional internal arguments for the route.

    Returns:
        RouteDef: The route definition object for the PUT request.
    """
    return route(
        # aiohttp attrs
        method=METH_PUT,
        path=path,
        handler=handler,
        name=name,
        **kwargs,
        # rapidy attrs
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


def patch(
    path: str,
    handler: HandlerOrView,
    *,
    name: str | None = None,
    status_code: int | HTTPStatus = HTTPStatus.OK,
    response_validate: bool = True,
    response_type: Type[Any] | None | UnsetType = Unset,
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
) -> RouteDef:
    """Create a new RouteDef item for registering PATCH web-handler.

    Args:
        path (str): The resource path specification for the route.
        handler (HandlerOrView): The handler function or view for the route.
        name (Optional[str]): Optional resource name.
        status_code (int): The default status code to be used for the response.
        response_validate (bool): Determines whether the handler's response should be validated.
        response_type (Union[Type[Any], None, UnsetType]): The type of response expected.
        response_content_type (Union[str, ContentType, None]): Defines the `Content-Type` header for the response.
        response_charset (Union[str, Charset]): Charset used for encoding and decoding the response.
        response_zlib_executor (Optional[Executor]): Executor for zlib compression.
        response_zlib_executor_size (Optional[int]): The size threshold for triggering zlib compression.
        response_include_fields (Optional[Include]): Fields to include during Pydantic model serialization.
        response_exclude_fields (Optional[Exclude]): Fields to exclude during Pydantic model serialization.
        response_by_alias (bool): Whether to use aliases for fields during serialization.
        response_exclude_unset (bool): Whether to exclude unset fields from the response.
        response_exclude_defaults (bool): Whether to exclude fields with default values from the response.
        response_exclude_none (bool): Whether to exclude fields with `None` values from the response.
        response_custom_encoder (Optional[CustomEncoder]): A custom encoder for Pydantic models.
        response_json_encoder (JSONEncoder): Custom JSON encoder function for serializing the response.
        kwargs (Any): Additional internal arguments for the route.

    Returns:
        RouteDef: The route definition object for the PATCH request.
    """
    return route(
        # aiohttp attrs
        method=METH_PATCH,
        path=path,
        handler=handler,
        name=name,
        **kwargs,
        # rapidy attrs
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


def delete(
    path: str,
    handler: HandlerOrView,
    *,
    name: str | None = None,
    status_code: int | HTTPStatus = HTTPStatus.OK,
    response_validate: bool = True,
    response_type: Type[Any] | None | UnsetType = Unset,
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
) -> RouteDef:
    """Create a new RouteDef item for registering DELETE web-handler.

    Args:
        path (str): The resource path specification for the route.
        handler (HandlerOrView): The handler function or view for the route.
        name (Optional[str]): Optional resource name.
        status_code (int): The default status code to be used for the response.
        response_validate (bool): Determines whether the handler's response should be validated.
        response_type (Union[Type[Any], None, UnsetType]): The type of response expected.
        response_content_type (Union[str, ContentType, None]): Defines the `Content-Type` header for the response.
        response_charset (Union[str, Charset]): Charset used for encoding and decoding the response.
        response_zlib_executor (Optional[Executor]): Executor for zlib compression.
        response_zlib_executor_size (Optional[int]): The size threshold for triggering zlib compression.
        response_include_fields (Optional[Include]): Fields to include during Pydantic model serialization.
        response_exclude_fields (Optional[Exclude]): Fields to exclude during Pydantic model serialization.
        response_by_alias (bool): Whether to use aliases for fields during serialization.
        response_exclude_unset (bool): Whether to exclude unset fields from the response.
        response_exclude_defaults (bool): Whether to exclude fields with default values from the response.
        response_exclude_none (bool): Whether to exclude fields with `None` values from the response.
        response_custom_encoder (Optional[CustomEncoder]): A custom encoder for Pydantic models.
        response_json_encoder (JSONEncoder): Custom JSON encoder function for serializing the response.
        kwargs (Any): Additional internal arguments for the route.

    Returns:
        RouteDef: The route definition object for the DELETE request.
    """
    return route(
        # aiohttp attrs
        method=METH_DELETE,
        path=path,
        handler=handler,
        name=name,
        **kwargs,
        # rapidy attrs
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


def view(
    path: str,
    handler: Type[AbstractView],
    *,
    name: str | None = None,
    status_code: int | HTTPStatus = HTTPStatus.OK,
    response_validate: bool = True,
    response_type: Type[Any] | None | UnsetType = Unset,
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
) -> RouteDef:
    """Create a new RouteDef item for adding class-based view handler.

    Args:
        path (str): The resource path specification for the route.
        handler (HandlerOrView): The handler function or view for the route.
        name (Optional[str]): Optional resource name.
        status_code (int): The default status code to be used for the response.
        response_validate (bool): Determines whether the handler's response should be validated.
        response_type (Union[Type[Any], None, UnsetType]): The type of response expected.
        response_content_type (Union[str, ContentType, None]): Defines the `Content-Type` header for the response.
        response_charset (Union[str, Charset]): Charset used for encoding and decoding the response.
        response_zlib_executor (Optional[Executor]): Executor for zlib compression.
        response_zlib_executor_size (Optional[int]): The size threshold for triggering zlib compression.
        response_include_fields (Optional[Include]): Fields to include during Pydantic model serialization.
        response_exclude_fields (Optional[Exclude]): Fields to exclude during Pydantic model serialization.
        response_by_alias (bool): Whether to use aliases for fields during serialization.
        response_exclude_unset (bool): Whether to exclude unset fields from the response.
        response_exclude_defaults (bool): Whether to exclude fields with default values from the response.
        response_exclude_none (bool): Whether to exclude fields with `None` values from the response.
        response_custom_encoder (Optional[CustomEncoder]): A custom encoder for Pydantic models.
        response_json_encoder (JSONEncoder): Custom JSON encoder function for serializing the response.
        kwargs (Any): Additional internal arguments for the route.

    Returns:
        RouteDef: The route definition object for a class-based view.
    """
    return route(
        # aiohttp attrs
        method=METH_ANY,
        path=path,
        handler=handler,
        name=name,
        **kwargs,
        # rapidy attrs
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


def head(
    path: str,
    handler: HandlerOrView,
    *,
    name: str | None = None,
    status_code: int | HTTPStatus = HTTPStatus.OK,
    response_validate: bool = True,
    response_type: Type[Any] | None | UnsetType = Unset,
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
) -> RouteDef:
    """Create a new RouteDef item for registering HEAD web-handler.

    Args:
        path (str): The resource path specification for the route.
        handler (HandlerOrView): The handler function or view for the route.
        name (Optional[str]): Optional resource name.
        status_code (int): The default status code to be used for the response.
        response_validate (bool): Determines whether the handler's response should be validated.
        response_type (Union[Type[Any], None, UnsetType]): The type of response expected.
        response_content_type (Union[str, ContentType, None]): Defines the `Content-Type` header for the response.
        response_charset (Union[str, Charset]): Charset used for encoding and decoding the response.
        response_zlib_executor (Optional[Executor]): Executor for zlib compression.
        response_zlib_executor_size (Optional[int]): The size threshold for triggering zlib compression.
        response_include_fields (Optional[Include]): Fields to include during Pydantic model serialization.
        response_exclude_fields (Optional[Exclude]): Fields to exclude during Pydantic model serialization.
        response_by_alias (bool): Whether to use aliases for fields during serialization.
        response_exclude_unset (bool): Whether to exclude unset fields from the response.
        response_exclude_defaults (bool): Whether to exclude fields with default values from the response.
        response_exclude_none (bool): Whether to exclude fields with `None` values from the response.
        response_custom_encoder (Optional[CustomEncoder]): A custom encoder for Pydantic models.
        response_json_encoder (JSONEncoder): Custom JSON encoder function for serializing the response.
        kwargs (Any): Additional internal arguments for the route.

    Returns:
        RouteDef: The route definition object for the HEAD request.
    """
    return route(
        # aiohttp attrs
        method=METH_HEAD,
        path=path,
        handler=handler,
        name=name,
        **kwargs,
        # rapidy attrs
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


def options(
    path: str,
    handler: HandlerOrView,
    *,
    name: str | None = None,
    status_code: int | HTTPStatus = HTTPStatus.OK,
    response_validate: bool = True,
    response_type: Type[Any] | None | UnsetType = Unset,
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
) -> RouteDef:
    """Create a new RouteDef item for registering OPTIONS web-handler.

    Args:
        path (str): The resource path specification for the route.
        handler (HandlerOrView): The handler function or view for the route.
        name (Optional[str]): Optional resource name.
        status_code (int): The default status code to be used for the response.
        response_validate (bool): Determines whether the handler's response should be validated.
        response_type (Union[Type[Any], None, UnsetType]): The type of response expected.
        response_content_type (Union[str, ContentType, None]): Defines the `Content-Type` header for the response.
        response_charset (Union[str, Charset]): Charset used for encoding and decoding the response.
        response_zlib_executor (Optional[Executor]): Executor for zlib compression.
        response_zlib_executor_size (Optional[int]): The size threshold for triggering zlib compression.
        response_include_fields (Optional[Include]): Fields to include during Pydantic model serialization.
        response_exclude_fields (Optional[Exclude]): Fields to exclude during Pydantic model serialization.
        response_by_alias (bool): Whether to use aliases for fields during serialization.
        response_exclude_unset (bool): Whether to exclude unset fields from the response.
        response_exclude_defaults (bool): Whether to exclude fields with default values from the response.
        response_exclude_none (bool): Whether to exclude fields with `None` values from the response.
        response_custom_encoder (Optional[CustomEncoder]): A custom encoder for Pydantic models.
        response_json_encoder (JSONEncoder): Custom JSON encoder function for serializing the response.
        kwargs (Any): Additional internal arguments for the route.

    Returns:
        RouteDef: The route definition object for the OPTIONS request.
    """
    return route(
        # aiohttp attrs
        method=METH_OPTIONS,
        path=path,
        handler=handler,
        name=name,
        **kwargs,
        # rapidy attrs
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


def static(prefix: str, path: PathLike, **kwargs: Any) -> StaticDef:
    """Create a new StaticDef item.

    Args:
        prefix (str): The prefix for the static route.
        path (PathLike): The path to the static file or directory.
        kwargs (Any): Additional arguments passed to StaticDef.

    Returns:
        StaticDef: A new StaticDef item.
    """
    return StaticDef(prefix, path, kwargs)


class RouteTableDef(AioHTTPRouteTableDef):
    """Overridden aiohttp RouteTableDef to handle custom route registration."""

    def route(self, method: str, path: str, **kwargs: Any) -> RouterDeco:
        """Register a handler for a given HTTP method and path.

        Args:
            method (str): HTTP method (GET, POST, etc.).
            path (str): The resource path.
            kwargs (Any): Additional internal arguments passed to RouteDef.

        Returns:
            RouterDeco: A decorator function to register the route handler.
        """

        def inner(handler: HandlerOrView) -> HandlerOrView:
            self._items.append(RouteDef(method, path, handler, kwargs))
            return handler

        return inner

    def get(
        self,
        path: str,
        *,
        name: str | None = None,
        allow_head: bool = True,
        status_code: int | HTTPStatus = HTTPStatus.OK,
        response_validate: bool = True,
        response_type: Type[Any] | None | UnsetType = Unset,
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
    ) -> RouterDeco:
        """Add a new RouteDef item for registering a GET web-handler.

        Args:
            path (str): The resource path specification for the route.
            name (Optional[str]): Optional resource name.
            allow_head (bool): If True (default), allows a HEAD route with the same handler as GET.
            status_code (int): The default status code to be used for the response.
            response_validate (bool): Determines whether the handler's response should be validated.
            response_type (Union[Type[Any], None, UnsetType]): The type of response expected.
            response_content_type (Union[str, ContentType, None]): Defines the `Content-Type` header for the response.
            response_charset (Union[str, Charset]): Charset used for encoding and decoding the response.
            response_zlib_executor (Optional[Executor]): Executor for zlib compression.
            response_zlib_executor_size (Optional[int]): The size threshold for triggering zlib compression.
            response_include_fields (Optional[Include]): Fields to include during Pydantic model serialization.
            response_exclude_fields (Optional[Exclude]): Fields to exclude during Pydantic model serialization.
            response_by_alias (bool): Whether to use aliases for fields during serialization.
            response_exclude_unset (bool): Whether to exclude unset fields from the response.
            response_exclude_defaults (bool): Whether to exclude fields with default values from the response.
            response_exclude_none (bool): Whether to exclude fields with `None` values from the response.
            response_custom_encoder (Optional[CustomEncoder]): A custom encoder for Pydantic models.
            response_json_encoder (JSONEncoder): Custom JSON encoder function for serializing the response.
            kwargs (Any): Additional internal arguments for the route.

        Returns:
            RouterDeco: A decorator function to register the GET route handler.
        """
        return self.route(
            # aiohttp attrs
            METH_GET,
            path,
            name=name,
            allow_head=allow_head,
            **kwargs,
            # rapidy attrs
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

    def post(
        self,
        path: str,
        *,
        name: str | None = None,
        status_code: int | HTTPStatus = HTTPStatus.OK,
        response_validate: bool = True,
        response_type: Type[Any] | None | UnsetType = Unset,
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
    ) -> RouterDeco:
        """Add a new RouteDef item for registering a POST web-handler.

        Args:
            path (str): The resource path specification for the route.
            name (Optional[str]): Optional resource name.
            status_code (int): The default status code to be used for the response.
            response_validate (bool): Determines whether the handler's response should be validated.
            response_type (Union[Type[Any], None, UnsetType]): The type of response expected.
            response_content_type (Union[str, ContentType, None]): Defines the `Content-Type` header for the response.
            response_charset (Union[str, Charset]): Charset used for encoding and decoding the response.
            response_zlib_executor (Optional[Executor]): Executor for zlib compression.
            response_zlib_executor_size (Optional[int]): The size threshold for triggering zlib compression.
            response_include_fields (Optional[Include]): Fields to include during Pydantic model serialization.
            response_exclude_fields (Optional[Exclude]): Fields to exclude during Pydantic model serialization.
            response_by_alias (bool): Whether to use aliases for fields during serialization.
            response_exclude_unset (bool): Whether to exclude unset fields from the response.
            response_exclude_defaults (bool): Whether to exclude fields with default values from the response.
            response_exclude_none (bool): Whether to exclude fields with `None` values from the response.
            response_custom_encoder (Optional[CustomEncoder]): A custom encoder for Pydantic models.
            response_json_encoder (JSONEncoder): Custom JSON encoder function for serializing the response.
            kwargs (Any): Additional internal arguments for the route.

        Returns:
            RouterDeco: A decorator function to register the POST route handler.
        """
        return self.route(
            # aiohttp attrs
            METH_POST,
            path,
            name=name,
            **kwargs,
            # rapidy attrs
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

    def put(
        self,
        path: str,
        *,
        name: str | None = None,
        status_code: int | HTTPStatus = HTTPStatus.OK,
        response_validate: bool = True,
        response_type: Type[Any] | None | UnsetType = Unset,
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
    ) -> RouterDeco:
        """Add a new RouteDef item for registering a PUT web-handler.

        Args:
            path (str): The resource path specification for the route.
            name (Optional[str]): Optional resource name.
            status_code (int): The default status code to be used for the response.
            response_validate (bool): Determines whether the handler's response should be validated.
            response_type (Union[Type[Any], None, UnsetType]): The type of response expected.
            response_content_type (Union[str, ContentType, None]): Defines the `Content-Type` header for the response.
            response_charset (Union[str, Charset]): Charset used for encoding and decoding the response.
            response_zlib_executor (Optional[Executor]): Executor for zlib compression.
            response_zlib_executor_size (Optional[int]): The size threshold for triggering zlib compression.
            response_include_fields (Optional[Include]): Fields to include during Pydantic model serialization.
            response_exclude_fields (Optional[Exclude]): Fields to exclude during Pydantic model serialization.
            response_by_alias (bool): Whether to use aliases for fields during serialization.
            response_exclude_unset (bool): Whether to exclude unset fields from the response.
            response_exclude_defaults (bool): Whether to exclude fields with default values from the response.
            response_exclude_none (bool): Whether to exclude fields with `None` values from the response.
            response_custom_encoder (Optional[CustomEncoder]): A custom encoder for Pydantic models.
            response_json_encoder (JSONEncoder): Custom JSON encoder function for serializing the response.
            kwargs (Any): Additional internal arguments for the route.

        Returns:
            RouterDeco: A decorator function to register the PUT route handler.
        """
        return self.route(
            # aiohttp attrs
            METH_PUT,
            path,
            name=name,
            **kwargs,
            # rapidy attrs
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

    def patch(
        self,
        path: str,
        *,
        name: str | None = None,
        status_code: int | HTTPStatus = HTTPStatus.OK,
        response_validate: bool = True,
        response_type: Type[Any] | None | UnsetType = Unset,
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
    ) -> RouterDeco:
        """Add a new RouteDef item for registering a PATCH web-handler.

        Args:
            path (str): The resource path specification for the route.
            name (Optional[str]): Optional resource name.
            status_code (int): The default status code to be used for the response.
            response_validate (bool): Determines whether the handler's response should be validated.
            response_type (Union[Type[Any], None, UnsetType]): The type of response expected.
            response_content_type (Union[str, ContentType, None]): Defines the `Content-Type` header for the response.
            response_charset (Union[str, Charset]): Charset used for encoding and decoding the response.
            response_zlib_executor (Optional[Executor]): Executor for zlib compression.
            response_zlib_executor_size (Optional[int]): The size threshold for triggering zlib compression.
            response_include_fields (Optional[Include]): Fields to include during Pydantic model serialization.
            response_exclude_fields (Optional[Exclude]): Fields to exclude during Pydantic model serialization.
            response_by_alias (bool): Whether to use aliases for fields during serialization.
            response_exclude_unset (bool): Whether to exclude unset fields from the response.
            response_exclude_defaults (bool): Whether to exclude fields with default values from the response.
            response_exclude_none (bool): Whether to exclude fields with `None` values from the response.
            response_custom_encoder (Optional[CustomEncoder]): A custom encoder for Pydantic models.
            response_json_encoder (JSONEncoder): Custom JSON encoder function for serializing the response.
            kwargs (Any): Additional internal arguments for the route.

        Returns:
            RouterDeco: A decorator function to register the PATCH route handler.
        """
        return self.route(
            # aiohttp attrs
            METH_PATCH,
            path,
            name=name,
            **kwargs,
            # rapidy attrs
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

    def delete(
        self,
        path: str,
        *,
        name: str | None = None,
        status_code: int | HTTPStatus = HTTPStatus.OK,
        response_validate: bool = True,
        response_type: Type[Any] | None | UnsetType = Unset,
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
    ) -> RouterDeco:
        """Add a new RouteDef item for registering a DELETE web-handler.

        Args:
            path (str): The resource path specification for the route.
            name (Optional[str]): Optional resource name.
            status_code (int): The default status code to be used for the response.
            response_validate (bool): Determines whether the handler's response should be validated.
            response_type (Union[Type[Any], None, UnsetType]): The type of response expected.
            response_content_type (Union[str, ContentType, None]): Defines the `Content-Type` header for the response.
            response_charset (Union[str, Charset]): Charset used for encoding and decoding the response.
            response_zlib_executor (Optional[Executor]): Executor for zlib compression.
            response_zlib_executor_size (Optional[int]): The size threshold for triggering zlib compression.
            response_include_fields (Optional[Include]): Fields to include during Pydantic model serialization.
            response_exclude_fields (Optional[Exclude]): Fields to exclude during Pydantic model serialization.
            response_by_alias (bool): Whether to use aliases for fields during serialization.
            response_exclude_unset (bool): Whether to exclude unset fields from the response.
            response_exclude_defaults (bool): Whether to exclude fields with default values from the response.
            response_exclude_none (bool): Whether to exclude fields with `None` values from the response.
            response_custom_encoder (Optional[CustomEncoder]): A custom encoder for Pydantic models.
            response_json_encoder (JSONEncoder): Custom JSON encoder function for serializing the response.
            kwargs (Any): Additional internal arguments for the route.

        Returns:
            RouterDeco: A decorator function to register the DELETE route handler.
        """
        return self.route(
            # aiohttp attrs
            METH_DELETE,
            path,
            name=name,
            **kwargs,
            # rapidy attrs
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

    def head(
        self,
        path: str,
        *,
        name: str | None = None,
        status_code: int | HTTPStatus = HTTPStatus.OK,
        response_validate: bool = True,
        response_type: Type[Any] | None | UnsetType = Unset,
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
    ) -> RouterDeco:
        """Add a new RouteDef item for registering a HEAD web-handler.

        Args:
            path (str): The resource path specification for the route.
            name (Optional[str]): Optional resource name.
            status_code (int): The default status code to be used for the response.
            response_validate (bool): Determines whether the handler's response should be validated.
            response_type (Union[Type[Any], None, UnsetType]): The type of response expected.
            response_content_type (Union[str, ContentType, None]): Defines the `Content-Type` header for the response.
            response_charset (Union[str, Charset]): Charset used for encoding and decoding the response.
            response_zlib_executor (Optional[Executor]): Executor for zlib compression.
            response_zlib_executor_size (Optional[int]): The size threshold for triggering zlib compression.
            response_include_fields (Optional[Include]): Fields to include during Pydantic model serialization.
            response_exclude_fields (Optional[Exclude]): Fields to exclude during Pydantic model serialization.
            response_by_alias (bool): Whether to use aliases for fields during serialization.
            response_exclude_unset (bool): Whether to exclude unset fields from the response.
            response_exclude_defaults (bool): Whether to exclude fields with default values from the response.
            response_exclude_none (bool): Whether to exclude fields with `None` values from the response.
            response_custom_encoder (Optional[CustomEncoder]): A custom encoder for Pydantic models.
            response_json_encoder (JSONEncoder): Custom JSON encoder function for serializing the response.
            kwargs (Any): Additional internal arguments for the route.

        Returns:
            RouterDeco: A decorator function to register the HEAD route handler.
        """
        return self.route(
            # aiohttp attrs
            METH_HEAD,
            path,
            name=name,
            **kwargs,
            # rapidy attrs
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

    def options(
        self,
        path: str,
        *,
        name: str | None = None,
        status_code: int | HTTPStatus = HTTPStatus.OK,
        response_validate: bool = True,
        response_type: Type[Any] | None | UnsetType = Unset,
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
    ) -> RouterDeco:
        """Add a new RouteDef item for registering a OPTIONS web-handler.

        Args:
            path (str): The resource path specification for the route.
            name (Optional[str]): Optional resource name.
            status_code (int): The default status code to be used for the response.
            response_validate (bool): Determines whether the handler's response should be validated.
            response_type (Union[Type[Any], None, UnsetType]): The type of response expected.
            response_content_type (Union[str, ContentType, None]): Defines the `Content-Type` header for the response.
            response_charset (Union[str, Charset]): Charset used for encoding and decoding the response.
            response_zlib_executor (Optional[Executor]): Executor for zlib compression.
            response_zlib_executor_size (Optional[int]): The size threshold for triggering zlib compression.
            response_include_fields (Optional[Include]): Fields to include during Pydantic model serialization.
            response_exclude_fields (Optional[Exclude]): Fields to exclude during Pydantic model serialization.
            response_by_alias (bool): Whether to use aliases for fields during serialization.
            response_exclude_unset (bool): Whether to exclude unset fields from the response.
            response_exclude_defaults (bool): Whether to exclude fields with default values from the response.
            response_exclude_none (bool): Whether to exclude fields with `None` values from the response.
            response_custom_encoder (Optional[CustomEncoder]): A custom encoder for Pydantic models.
            response_json_encoder (JSONEncoder): Custom JSON encoder function for serializing the response.
            kwargs (Any): Additional internal arguments for the route.

        Returns:
            RouterDeco: A decorator function to register the OPTIONS route handler.
        """
        return self.route(
            # aiohttp attrs
            METH_OPTIONS,
            path,
            name=name,
            **kwargs,
            # rapidy attrs
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

    def view(
        self,
        path: str,
        *,
        name: str | None = None,
        status_code: int | HTTPStatus = HTTPStatus.OK,
        response_validate: bool = True,
        response_type: Type[Any] | None | UnsetType = Unset,
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
    ) -> RouterDeco:
        """Add a new RouteDef item for registering ANY methods for a class-based view.

        Args:
            path (str): The resource path specification for the route.
            name (Optional[str]): Optional resource name.
            status_code (int): The default status code to be used for the response.
            response_validate (bool): Determines whether the handler's response should be validated.
            response_type (Union[Type[Any], None, UnsetType]): The type of response expected.
            response_content_type (Union[str, ContentType, None]): Defines the `Content-Type` header for the response.
            response_charset (Union[str, Charset]): Charset used for encoding and decoding the response.
            response_zlib_executor (Optional[Executor]): Executor for zlib compression.
            response_zlib_executor_size (Optional[int]): The size threshold for triggering zlib compression.
            response_include_fields (Optional[Include]): Fields to include during Pydantic model serialization.
            response_exclude_fields (Optional[Exclude]): Fields to exclude during Pydantic model serialization.
            response_by_alias (bool): Whether to use aliases for fields during serialization.
            response_exclude_unset (bool): Whether to exclude unset fields from the response.
            response_exclude_defaults (bool): Whether to exclude fields with default values from the response.
            response_exclude_none (bool): Whether to exclude fields with `None` values from the response.
            response_custom_encoder (Optional[CustomEncoder]): A custom encoder for Pydantic models.
            response_json_encoder (JSONEncoder): Custom JSON encoder function for serializing the response.
            kwargs (Any): Additional internal arguments for the route.

        Returns:
            RouterDeco: A decorator function to register the class-based view.
        """
        return self.route(
            # aiohttp attrs
            METH_ANY,
            path,
            name=name,
            **kwargs,
            # rapidy attrs
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
