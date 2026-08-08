from __future__ import annotations

from abc import ABC
from concurrent.futures import Executor
from http import HTTPStatus
from types import FunctionType
from typing import Any, cast, Final, Type, TYPE_CHECKING

from aiohttp.hdrs import METH_ANY, METH_DELETE, METH_GET, METH_HEAD, METH_OPTIONS, METH_PATCH, METH_POST, METH_PUT
from aiohttp.typedefs import DEFAULT_JSON_ENCODER, JSONEncoder
from aiohttp.web_urldispatcher import (
    _ExpectHandler,
    _requote_path,
    AbstractResource,
    AbstractRoute,
    DynamicResource as AioHTTPDynamicResource,
    PlainResource as AioHTTPPlainResource,
    PrefixedSubAppResource,
    Resource as AioHTTPResource,
    ResourceRoute as AioHTTPResourceRoute,
    ROUTE_RE,
    StaticResource,
    UrlDispatcher as AioHTTPUrlDispatcher,
    UrlMappingMatchInfo,
    View,
)

from rapidy.annotation_checkers import lenient_issubclass
from rapidy.encoders import CustomEncoder, Exclude, Include
from rapidy.endpoint_handlers.http.handlers import handler_validation_wrapper, view_validation_wrapper
from rapidy.enums import Charset, ContentType, MethodName
from rapidy.routing.http.helper_types import HandlerPartial
from rapidy.typedefs import Handler, HandlerOrView, Unset, UnsetType

if TYPE_CHECKING:
    from aiohttp.abc import AbstractView

__all__ = [
    'UrlDispatcher',
    'UrlMappingMatchInfo',
    'AbstractResource',
    'Resource',
    'PlainResource',
    'PrefixedSubAppResource',
    'DynamicResource',
    'AbstractRoute',
    'ResourceRoute',
    'StaticResource',
    'View',
]

HEAD_METHOD_NAME: Final[str] = 'head'


def wrap_handler(
    *,
    handler: Handler | View,
    wrapper: Any,
    **kwargs: Any,
) -> Handler | View:
    """Wraps a handler with the specified wrapper function.

    Args:
        handler (Union[Handler, View]): The handler function or view to wrap.
        wrapper (Any): The wrapper function to apply to the handler.
        **kwargs (Any): Additional arguments passed to the wrapper function.

    Returns:
        Union[Handler, View]: The wrapped handler or view, after applying the wrapper.
    """
    return wrapper(
        handler,
        status_code=kwargs.pop('status_code'),
        response_validate=kwargs.pop('response_validate'),
        response_type=kwargs.pop('response_type'),
        response_content_type=kwargs.pop('response_content_type'),
        response_charset=kwargs.pop('response_charset'),
        response_zlib_executor=kwargs.pop('response_zlib_executor'),
        response_zlib_executor_size=kwargs.pop('response_zlib_executor_size'),
        response_include_fields=kwargs.pop('response_include_fields'),
        response_exclude_fields=kwargs.pop('response_exclude_fields'),
        response_by_alias=kwargs.pop('response_by_alias'),
        response_exclude_unset=kwargs.pop('response_exclude_unset'),
        response_exclude_defaults=kwargs.pop('response_exclude_defaults'),
        response_exclude_none=kwargs.pop('response_exclude_none'),
        response_custom_encoder=kwargs.pop('response_custom_encoder'),
        response_json_encoder=kwargs.pop('response_json_encoder'),
        **kwargs,
    )


class ResourceRoute(AioHTTPResourceRoute, ABC):
    """Overridden aiohttp ResourceRoute.

    This class extends the aiohttp's ResourceRoute and adds custom handling
    for different types of HTTP method handlers.
    """

    def __init__(
        self,
        method: str,
        handler: HandlerOrView,
        resource: AbstractResource,
        *,
        expect_handler: _ExpectHandler | None = None,
        **kwargs: Any,
    ) -> None:
        """Initializes the overridden aiohttp ResourceRoute.

        Args:
            method (str): HTTP method (e.g., 'GET', 'POST').
            handler (HandlerOrView): The handler function or view associated with the route.
            resource (AbstractResource): The associated resource for the route.
            expect_handler (Optional[_ExpectHandler]): Optional handler for expected request behavior.
            **kwargs (Any): Additional arguments for wrapping the handler.
        """
        if isinstance(handler, FunctionType | HandlerPartial):
            handler = wrap_handler(handler=handler, wrapper=handler_validation_wrapper, **kwargs)
        elif lenient_issubclass(handler, View):
            handler = wrap_handler(
                handler=handler,
                wrapper=view_validation_wrapper,
                method=MethodName(method),
                **kwargs,
            )

        super().__init__(method=method, handler=handler, expect_handler=expect_handler, resource=resource)


class Resource(AioHTTPResource, ABC):
    """Overridden aiohttp Resource.

    This class extends the aiohttp Resource to manage route registration and
    validation with custom handling for various HTTP methods.
    """

    def add_route(
        self,
        method: str,
        handler: HandlerOrView,
        *,
        expect_handler: _ExpectHandler | None = None,
        **kwargs: Any,
    ) -> ResourceRoute:
        """Adds a route to the overridden aiohttp Resource.

        Args:
            method (str): HTTP method (e.g., 'GET', 'POST').
            handler (HandlerOrView): The handler function or view to associate with the route.
            expect_handler (Optional[_ExpectHandler]): Optional handler for the 'Expect' header.
            **kwargs (Any): Additional arguments for wrapping the handler.

        Returns:
            ResourceRoute: The created `ResourceRoute` instance associated with the handler.

        Raises:
            RuntimeError: If a route with the same method is already registered.
        """
        for route_obj in self._routes:
            route_method = route_obj.method if isinstance(route_obj, ResourceRoute) else route_obj  # aiohttp > 3.11
            if route_method == method in (method, METH_ANY):
                raise RuntimeError(  # aiohttp code  # pragma: no cover  # noqa: TRY003
                    f'Added route will never be executed, method {route_method} is already registered',  # noqa: EM102
                )

        route_obj = ResourceRoute(method, handler, self, expect_handler=expect_handler, **kwargs)
        self.register_route(route_obj)

        return route_obj


class PlainResource(Resource, AioHTTPPlainResource):
    """Represents a plain resource without dynamic path parameters."""


class DynamicResource(Resource, AioHTTPDynamicResource):
    """Represents a dynamic resource with path parameters."""


class UrlDispatcher(AioHTTPUrlDispatcher):
    """Custom URL dispatcher extending aiohttp's UrlDispatcher."""

    def add_resource(self, path: str, *, name: str | None = None) -> Resource:
        """Adds a new resource.

        Args:
            path (str): The resource path.
            name (Optional[str]): Optional resource name.

        Returns:
            Resource: The created Resource instance.

        Raises:
            ValueError: If the path doesn't start with '/'.
        """
        if path and not path.startswith('/'):  # aiohttp code  # pragma: no cover
            raise ValueError('path should start with / or be empty')  # noqa: TRY003

        # Reuse last added resource if path and name are the same
        if self._resources:
            resource = self._resources[-1]
            if resource.name == name and resource.raw_match(path):
                return cast(Resource, resource)

        if not ('{' in path or '}' in path or ROUTE_RE.search(path)):
            resource = PlainResource(_requote_path(path), name=name)
            self.register_resource(resource)
            return resource

        resource = DynamicResource(path, name=name)
        self.register_resource(resource)

        return resource

    def add_route(
        self,
        method: str,
        path: str,
        handler: HandlerOrView,
        *,
        name: str | None = None,
        expect_handler: _ExpectHandler | None = None,
        **kwargs: Any,
    ) -> AbstractRoute:
        """Registers a handler for a specific HTTP method and path.

        Args:
            method (str): HTTP method name.
            path (str): Resource path spec.
            handler (HandlerOrView): The HTTP handler function or view.
            name (Optional[str]): Optional resource name.
            expect_handler (Optional[_ExpectHandler]): Optional expect header handler.
            kwargs (Any): Additional internal arguments.

        Returns:
            AbstractRoute: The created AbstractRoute instance.
        """
        resource = self.add_resource(path, name=name)
        return resource.add_route(method, handler, expect_handler=expect_handler, **kwargs)

    def add_get(
        self,
        path: str,
        handler: HandlerOrView,
        *,
        name: str | None = None,
        allow_head: bool = True,
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
        **kwargs: Any,
    ) -> AbstractRoute:
        """Shortcut for registering a GET route.

        Args:
            path (str): Resource path spec.
            handler (HandlerOrView): Route handler.
            name (Optional[str]): Optional resource name.
            allow_head (bool): If True (default), allows a HEAD route with the same handler as GET.
            status_code (int): The default status code to be used for the response.
            response_validate (bool): Flag determining if the handler response should be validated.
            response_type (Union[Type[Any], None, UnsetType]): Handler response type, overrides the
                                                               return annotation if set.
            response_content_type (Union[str, ContentType, None]): Defines the `Content-Type` header for the response.
            response_charset (Union[str, Charset]): Charset to use for encoding/decoding response data.
            response_zlib_executor (Optional[Executor]): Executor to use for zlib compression.
            response_zlib_executor_size (Optional[int]): Length in bytes triggering zlib compression.
            response_include_fields (Optional[Include]): Pydantic's `include` parameter for including specific fields
                                                         in the response.
            response_exclude_fields (Optional[Exclude]): Pydantic's `exclude` parameter for excluding specific fields
                                                         from the response.
            response_by_alias (bool): If True, uses alias names (if set) instead of Python attribute names.
            response_exclude_unset (bool): If True, excludes fields that were not explicitly set.
            response_exclude_defaults (bool): If True, excludes fields with default values.
            response_exclude_none (bool): If True, excludes fields with `None` values.
            response_custom_encoder (Optional[CustomEncoder]): Custom encoder for the response.
            response_json_encoder (JSONEncoder): Encoder used to serialize the response.
            kwargs (Any): Additional internal arguments.

        Returns:
            AbstractRoute: The created AbstractRoute instance.
        """
        resource = self.add_resource(path, name=name)
        if allow_head:
            resource.add_route(
                METH_HEAD,
                handler,
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
        return resource.add_route(
            METH_GET,
            handler,
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

    def add_post(
        self,
        path: str,
        handler: HandlerOrView,
        *,
        name: str | None = None,
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
        **kwargs: Any,
    ) -> AbstractRoute:
        """Shortcut for registering a POST route.

        Args:
            path (str): Resource path spec.
            handler (HandlerOrView): Route handler.
            name (Optional[str]): Optional resource name.
            status_code (int): The default status code to be used for the response.
            response_validate (bool): Flag determining if the handler response should be validated.
            response_type (Union[Type[Any], None, UnsetType]): Handler response type, overrides the
                                                               return annotation if set.
            response_content_type (Union[str, ContentType, None]): Defines the `Content-Type` header for the response.
            response_charset (Union[str, Charset]): Charset to use for encoding/decoding response data.
            response_zlib_executor (Optional[Executor]): Executor to use for zlib compression.
            response_zlib_executor_size (Optional[int]): Length in bytes triggering zlib compression.
            response_include_fields (Optional[Include]): Pydantic's `include` parameter for including specific fields
                                                         in the response.
            response_exclude_fields (Optional[Exclude]): Pydantic's `exclude` parameter for excluding specific fields
                                                         from the response.
            response_by_alias (bool): If True, uses alias names (if set) instead of Python attribute names.
            response_exclude_unset (bool): If True, excludes fields that were not explicitly set.
            response_exclude_defaults (bool): If True, excludes fields with default values.
            response_exclude_none (bool): If True, excludes fields with `None` values.
            response_custom_encoder (Optional[CustomEncoder]): Custom encoder for the response.
            response_json_encoder (JSONEncoder): Encoder used to serialize the response.
            kwargs (Any): Additional internal arguments.

        Returns:
            AbstractRoute: The created AbstractRoute instance.
        """
        return self.add_route(
            # aiohttp attrs
            METH_POST,
            path,
            handler,
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

    def add_put(
        self,
        path: str,
        handler: HandlerOrView,
        *,
        name: str | None = None,
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
        **kwargs: Any,
    ) -> AbstractRoute:
        """Shortcut for registering a PUT route.

        Args:
            path (str): Resource path spec.
            handler (HandlerOrView): Route handler.
            name (Optional[str]): Optional resource name.
            status_code (int): The default status code to be used for the response.
            response_validate (bool): Flag determining if the handler response should be validated.
            response_type (Union[Type[Any], None, UnsetType]): Handler response type, overrides the
                                                               return annotation if set.
            response_content_type (Union[str, ContentType, None]): Defines the `Content-Type` header for the response.
            response_charset (Union[str, Charset]): Charset to use for encoding/decoding response data.
            response_zlib_executor (Optional[Executor]): Executor to use for zlib compression.
            response_zlib_executor_size (Optional[int]): Length in bytes triggering zlib compression.
            response_include_fields (Optional[Include]): Pydantic's `include` parameter for including specific fields
                                                         in the response.
            response_exclude_fields (Optional[Exclude]): Pydantic's `exclude` parameter for excluding specific fields
                                                         from the response.
            response_by_alias (bool): If True, uses alias names (if set) instead of Python attribute names.
            response_exclude_unset (bool): If True, excludes fields that were not explicitly set.
            response_exclude_defaults (bool): If True, excludes fields with default values.
            response_exclude_none (bool): If True, excludes fields with `None` values.
            response_custom_encoder (Optional[CustomEncoder]): Custom encoder for the response.
            response_json_encoder (JSONEncoder): Encoder used to serialize the response.
            kwargs (Any): Additional internal arguments.

        Returns:
            AbstractRoute: The created AbstractRoute instance.
        """
        return self.add_route(
            # aiohttp attrs
            METH_PUT,
            path,
            handler,
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

    def add_patch(
        self,
        path: str,
        handler: HandlerOrView,
        *,
        name: str | None = None,
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
        **kwargs: Any,
    ) -> AbstractRoute:
        """Shortcut for registering a PATCH route.

        Args:
            path (str): Resource path spec.
            handler (HandlerOrView): Route handler.
            name (Optional[str]): Optional resource name.
            status_code (int): The default status code to be used for the response.
            response_validate (bool): Flag determining if the handler response should be validated.
            response_type (Union[Type[Any], None, UnsetType]): Handler response type, overrides the
                                                               return annotation if set.
            response_content_type (Union[str, ContentType, None]): Defines the `Content-Type` header for the response.
            response_charset (Union[str, Charset]): Charset to use for encoding/decoding response data.
            response_zlib_executor (Optional[Executor]): Executor to use for zlib compression.
            response_zlib_executor_size (Optional[int]): Length in bytes triggering zlib compression.
            response_include_fields (Optional[Include]): Pydantic's `include` parameter for including specific fields
                                                         in the response.
            response_exclude_fields (Optional[Exclude]): Pydantic's `exclude` parameter for excluding specific fields
                                                         from the response.
            response_by_alias (bool): If True, uses alias names (if set) instead of Python attribute names.
            response_exclude_unset (bool): If True, excludes fields that were not explicitly set.
            response_exclude_defaults (bool): If True, excludes fields with default values.
            response_exclude_none (bool): If True, excludes fields with `None` values.
            response_custom_encoder (Optional[CustomEncoder]): Custom encoder for the response.
            response_json_encoder (JSONEncoder): Encoder used to serialize the response.
            kwargs (Any): Additional internal arguments.

        Returns:
            AbstractRoute: The created AbstractRoute instance.
        """
        return self.add_route(
            # aiohttp attrs
            METH_PATCH,
            path,
            handler,
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

    def add_delete(
        self,
        path: str,
        handler: HandlerOrView,
        *,
        name: str | None = None,
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
        **kwargs: Any,
    ) -> AbstractRoute:
        """Shortcut for registering a DELETE route.

        Args:
            path (str): Resource path spec.
            handler (HandlerOrView): Route handler.
            name (Optional[str]): Optional resource name.
            status_code (int): The default status code to be used for the response.
            response_validate (bool): Flag determining if the handler response should be validated.
            response_type (Union[Type[Any], None, UnsetType]): Handler response type, overrides the
                                                               return annotation if set.
            response_content_type (Union[str, ContentType, None]): Defines the `Content-Type` header for the response.
            response_charset (Union[str, Charset]): Charset to use for encoding/decoding response data.
            response_zlib_executor (Optional[Executor]): Executor to use for zlib compression.
            response_zlib_executor_size (Optional[int]): Length in bytes triggering zlib compression.
            response_include_fields (Optional[Include]): Pydantic's `include` parameter for including specific fields
                                                         in the response.
            response_exclude_fields (Optional[Exclude]): Pydantic's `exclude` parameter for excluding specific fields
                                                         from the response.
            response_by_alias (bool): If True, uses alias names (if set) instead of Python attribute names.
            response_exclude_unset (bool): If True, excludes fields that were not explicitly set.
            response_exclude_defaults (bool): If True, excludes fields with default values.
            response_exclude_none (bool): If True, excludes fields with `None` values.
            response_custom_encoder (Optional[CustomEncoder]): Custom encoder for the response.
            response_json_encoder (JSONEncoder): Encoder used to serialize the response.
            kwargs (Any): Additional internal arguments.

        Returns:
            AbstractRoute: The created AbstractRoute instance.
        """
        return self.add_route(
            METH_DELETE,
            path,
            handler,
            name=name,
            **kwargs,
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

    def add_head(
        self,
        path: str,
        handler: HandlerOrView,
        *,
        name: str | None = None,
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
        **kwargs: Any,
    ) -> AbstractRoute:
        """Shortcut for registering a HEAD route.

        Args:
            path (str): Resource path spec.
            handler (HandlerOrView): Route handler.
            name (Optional[str]): Optional resource name.
            status_code (int): The default status code to be used for the response.
            response_validate (bool): Flag determining if the handler response should be validated.
            response_type (Union[Type[Any], None, UnsetType]): Handler response type, overrides the
                                                               return annotation if set.
            response_content_type (Union[str, ContentType, None]): Defines the `Content-Type` header for the response.
            response_charset (Union[str, Charset]): Charset to use for encoding/decoding response data.
            response_zlib_executor (Optional[Executor]): Executor to use for zlib compression.
            response_zlib_executor_size (Optional[int]): Length in bytes triggering zlib compression.
            response_include_fields (Optional[Include]): Pydantic's `include` parameter for including specific fields
                                                         in the response.
            response_exclude_fields (Optional[Exclude]): Pydantic's `exclude` parameter for excluding specific fields
                                                         from the response.
            response_by_alias (bool): If True, uses alias names (if set) instead of Python attribute names.
            response_exclude_unset (bool): If True, excludes fields that were not explicitly set.
            response_exclude_defaults (bool): If True, excludes fields with default values.
            response_exclude_none (bool): If True, excludes fields with `None` values.
            response_custom_encoder (Optional[CustomEncoder]): Custom encoder for the response.
            response_json_encoder (JSONEncoder): Encoder used to serialize the response.
            kwargs (Any): Additional internal arguments.

        Returns:
            AbstractRoute: The created AbstractRoute instance.
        """
        return self.add_route(
            # aiohttp attrs
            METH_HEAD,
            path,
            handler,
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

    def add_options(
        self,
        path: str,
        handler: HandlerOrView,
        *,
        name: str | None = None,
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
        **kwargs: Any,
    ) -> AbstractRoute:
        """Shortcut for registering a OPTIONS route.

        Args:
            path (str): Resource path spec.
            handler (HandlerOrView): Route handler.
            name (Optional[str]): Optional resource name.
            status_code (int): The default status code to be used for the response.
            response_validate (bool): Flag determining if the handler response should be validated.
            response_type (Union[Type[Any], None, UnsetType]): Handler response type, overrides the
                                                               return annotation if set.
            response_content_type (Union[str, ContentType, None]): Defines the `Content-Type` header for the response.
            response_charset (Union[str, Charset]): Charset to use for encoding/decoding response data.
            response_zlib_executor (Optional[Executor]): Executor to use for zlib compression.
            response_zlib_executor_size (Optional[int]): Length in bytes triggering zlib compression.
            response_include_fields (Optional[Include]): Pydantic's `include` parameter for including specific fields
                                                         in the response.
            response_exclude_fields (Optional[Exclude]): Pydantic's `exclude` parameter for excluding specific fields
                                                         from the response.
            response_by_alias (bool): If True, uses alias names (if set) instead of Python attribute names.
            response_exclude_unset (bool): If True, excludes fields that were not explicitly set.
            response_exclude_defaults (bool): If True, excludes fields with default values.
            response_exclude_none (bool): If True, excludes fields with `None` values.
            response_custom_encoder (Optional[CustomEncoder]): Custom encoder for the response.
            response_json_encoder (JSONEncoder): Encoder used to serialize the response.
            kwargs (Any): Additional internal arguments.

        Returns:
            AbstractRoute: The created AbstractRoute instance.
        """
        return self.add_route(
            # aiohttp attrs
            METH_OPTIONS,
            path,
            handler,
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

    def add_view(
        self,
        path: str,
        handler: Type[AbstractView],
        *,
        name: str | None = None,
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
        **kwargs: Any,
    ) -> AbstractRoute:
        """Shortcut for `add_route` with ANY methods for a class-based view.

        Args:
            path (str): Resource path spec.
            handler (HandlerOrView): Route handler.
            name (Optional[str]): Optional resource name.
            status_code (int): The default status code to be used for the response.
            response_validate (bool): Flag determining if the handler response should be validated.
            response_type (Union[Type[Any], None, UnsetType]): Handler response type, overrides the
                                                               return annotation if set.
            response_content_type (Union[str, ContentType, None]): Defines the `Content-Type` header for the response.
            response_charset (Union[str, Charset]): Charset to use for encoding/decoding response data.
            response_zlib_executor (Optional[Executor]): Executor to use for zlib compression.
            response_zlib_executor_size (Optional[int]): Length in bytes triggering zlib compression.
            response_include_fields (Optional[Include]): Pydantic's `include` parameter for including specific fields
                                                         in the response.
            response_exclude_fields (Optional[Exclude]): Pydantic's `exclude` parameter for excluding specific fields
                                                         from the response.
            response_by_alias (bool): If True, uses alias names (if set) instead of Python attribute names.
            response_exclude_unset (bool): If True, excludes fields that were not explicitly set.
            response_exclude_defaults (bool): If True, excludes fields with default values.
            response_exclude_none (bool): If True, excludes fields with `None` values.
            response_custom_encoder (Optional[CustomEncoder]): Custom encoder for the response.
            response_json_encoder (JSONEncoder): Encoder used to serialize the response.
            kwargs (Any): Additional internal arguments.

        Returns:
            AbstractRoute: The created AbstractRoute instance.
        """
        return self.add_route(
            # aiohttp attrs
            METH_ANY,
            path,
            handler,
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
