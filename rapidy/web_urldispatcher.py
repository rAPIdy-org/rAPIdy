from abc import ABC
from types import FunctionType
from typing import Any, Awaitable, Callable, cast, Optional, Type, Union

from aiohttp.abc import AbstractView
from aiohttp.typedefs import Handler
from aiohttp.web_request import Request
from aiohttp.web_response import StreamResponse
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
    View as AioHTTPView,
)

from rapidy import hdrs
from rapidy._annotation_container import AnnotationContainer, create_annotation_container

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


class ResourceRoute(AioHTTPResourceRoute, ABC):
    def __init__(
            self,
            method: str,
            handler: Union[Handler, Type[AbstractView]],
            resource: AbstractResource,
            *,
            expect_handler: Optional[_ExpectHandler] = None,
    ) -> None:
        super().__init__(
            method=method,
            handler=handler,
            expect_handler=expect_handler,
            resource=resource,
        )

        self.annotation_container = {}

        if isinstance(handler, FunctionType):
            self.annotation_container[method.lower()] = create_annotation_container(handler)

        elif issubclass(handler, AbstractView):
            for method in (  # noqa: WPS335 WPS352 WPS440
                handler_attr
                for handler_attr in dir(handler)
                if handler_attr.upper() in hdrs.METH_ALL
            ):
                method_handler: Optional[Callable[[], Awaitable[StreamResponse]]] = getattr(handler, method, None)
                if method_handler is None:  # NOTE: Scenario is impossible.  # pragma: no cover
                    raise

                self.annotation_container[method.lower()] = create_annotation_container(method_handler)

    def get_method_container(self, method: str) -> AnnotationContainer:
        return self.annotation_container[method.lower()]


class Resource(AioHTTPResource, ABC):
    def add_route(
        self,
        method: str,
        handler: Union[Type[AbstractView], Handler],
        *,
        expect_handler: Optional[_ExpectHandler] = None,
    ) -> 'ResourceRoute':

        for route_obj in self._routes:
            if route_obj.method == method or route_obj.method == hdrs.METH_ANY:  # noqa: WPS514
                raise RuntimeError(  # aiohttp code  # pragma: no cover
                    'Added route will never be executed, '
                    'method {route.method} is already '
                    'registered'.format(route=route_obj),
                )

        route_obj = ResourceRoute(method, handler, self, expect_handler=expect_handler)  # noqa: WPS440
        self.register_route(route_obj)  # noqa: WPS441

        return route_obj  # noqa: WPS441


class PlainResource(Resource, AioHTTPPlainResource):
    pass


class DynamicResource(Resource, AioHTTPDynamicResource):
    pass


class UrlDispatcher(AioHTTPUrlDispatcher):
    def add_resource(self, path: str, *, name: Optional[str] = None) -> Resource:
        if path and not path.startswith('/'):  # aiohttp code  # pragma: no cover
            raise ValueError('path should be started with / or be empty')

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


class View(AioHTTPView):
    def __init__(self, request: Request, **request_validated_data: Any) -> None:
        super().__init__(request)
        self._request_validated_data = request_validated_data

    async def _iter(self) -> StreamResponse:
        if self.request.method not in hdrs.METH_ALL:  # aiohttp code  # pragma: no cover
            self._raise_allowed_methods()

        method: Optional[Callable[[], Awaitable[StreamResponse]]]
        method = getattr(self, self.request.method.lower(), None)

        if method is None:  # aiohttp code  # pragma: no cover
            self._raise_allowed_methods()

        ret = await method(**self._request_validated_data)  # type: ignore[misc]

        assert isinstance(ret, StreamResponse)
        return ret
