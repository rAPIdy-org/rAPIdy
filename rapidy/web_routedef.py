from typing import Any, Optional

from aiohttp.web_routedef import (
    AbstractRouteDef,
    RouteDef,
    RouteTableDef as AioHTTPRouteTableDef,
    static,
    StaticDef,
    view,
)

from rapidy import hdrs
from rapidy.typedefs import HandlerType, RouterDeco

__all__ = (
    'AbstractRouteDef',
    'RouteDef',
    'StaticDef',
    'RouteTableDef',
    'head',
    'options',
    'get',
    'post',
    'patch',
    'put',
    'delete',
    'route',
    'view',
    'static',
)


def route(method: str, path: str, handler: HandlerType, **kwargs: Any) -> RouteDef:
    return RouteDef(method, path, handler, kwargs)


def head(path: str, handler: HandlerType, **kwargs: Any) -> RouteDef:
    return route(hdrs.METH_HEAD, path, handler, **kwargs)


def options(path: str, handler: HandlerType, **kwargs: Any) -> RouteDef:
    return route(hdrs.METH_OPTIONS, path, handler, **kwargs)


def get(
    path: str,
    handler: HandlerType,
    *,
    name: Optional[str] = None,
    allow_head: bool = True,
    **kwargs: Any,
) -> RouteDef:
    return route(
        hdrs.METH_GET, path, handler, name=name, allow_head=allow_head, **kwargs,
    )


def post(path: str, handler: HandlerType, **kwargs: Any) -> RouteDef:
    return route(hdrs.METH_POST, path, handler, **kwargs)


def put(path: str, handler: HandlerType, **kwargs: Any) -> RouteDef:
    return route(hdrs.METH_PUT, path, handler, **kwargs)


def patch(path: str, handler: HandlerType, **kwargs: Any) -> RouteDef:
    return route(hdrs.METH_PATCH, path, handler, **kwargs)


def delete(path: str, handler: HandlerType, **kwargs: Any) -> RouteDef:
    return route(hdrs.METH_DELETE, path, handler, **kwargs)


class RouteTableDef(AioHTTPRouteTableDef):
    def route(self, method: str, path: str, **kwargs: Any) -> RouterDeco:
        def inner(handler: HandlerType) -> HandlerType:
            self._items.append(RouteDef(method, path, handler, kwargs))
            return handler

        return inner

    def head(self, path: str, **kwargs: Any) -> RouterDeco:
        return self.route(hdrs.METH_HEAD, path, **kwargs)

    def get(self, path: str, **kwargs: Any) -> RouterDeco:
        return self.route(hdrs.METH_GET, path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> RouterDeco:
        return self.route(hdrs.METH_POST, path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> RouterDeco:
        return self.route(hdrs.METH_PUT, path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> RouterDeco:
        return self.route(hdrs.METH_PATCH, path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> RouterDeco:
        return self.route(hdrs.METH_DELETE, path, **kwargs)

    def options(self, path: str, **kwargs: Any) -> RouterDeco:
        return self.route(hdrs.METH_OPTIONS, path, **kwargs)

    def view(self, path: str, **kwargs: Any) -> RouterDeco:
        return self.route(hdrs.METH_ANY, path, **kwargs)
