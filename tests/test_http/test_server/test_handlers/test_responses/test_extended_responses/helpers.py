import inspect
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, Awaitable, Callable, Literal, Optional, Tuple, Type

from aiohttp.pytest_plugin import AiohttpClient
from pydantic import BaseModel
from typing_extensions import Final, TypeAlias

from rapidy import web
from rapidy.web_routedef import RouteTableDef

__all__ = (
    'PATH',
    'AppFabric',
    'DEFAULT_RETURN_TYPE',
    'DEFAULT_RETURN_VALUE',
    'test_dict',
    'TestBaseModel',
    'TestDataclass',
    'check_all_handlers',
    'check_all_handlers_with_all_response_model_flows',
)


AppFabric: TypeAlias = Callable[..., Tuple[web.Application, ...]]

PATH: Final[str] = '/'
WEB_METHOD_NAMES: Tuple[str, ...] = ('get', 'post', 'put', 'patch', 'delete', 'options')  # aiohttp head -> no return

DEFAULT_RETURN_TYPE: Type[str] = str
DEFAULT_RETURN_VALUE: Final[str] = 'test'

test_dict = {'test': DEFAULT_RETURN_VALUE}


class TestBaseModel(BaseModel):
    test: str = 'test'


@dataclass
class TestDataclass:
    test: str = 'test'


def get_bound_method_by_http_method_name(obj: Any, method_name: str) -> Any:
    return getattr(obj, method_name)


def create_app_use_route_table_def(
        handler: Any,
        web_method: str,
        **handler_kwargs: Any,
) -> web.Application:
    routes = RouteTableDef()
    method = get_bound_method_by_http_method_name(routes, web_method)
    method(PATH, **handler_kwargs)(handler)

    app = web.Application()
    app.add_routes(routes)

    return app


def create_app_use_simple_method_func(
        handler: Any,
        web_method: str,
        **handler_kwargs: Any,
) -> web.Application:
    method = get_bound_method_by_http_method_name(web, web_method)

    app = web.Application()
    app.add_routes([method(PATH, handler, **handler_kwargs)])

    return app


def create_app_use_app_router(
        handler: Any,
        web_method: str,
        **handler_kwargs: Any,
) -> web.Application:
    app = web.Application()
    method = get_bound_method_by_http_method_name(app.router, 'add_' + web_method)
    method(PATH, handler, **handler_kwargs)

    return app


def create_app_use_rapidy_router(
        handler: Any,
        web_method: str,
        **handler_kwargs: Any,
) -> web.Application:
    from rapidy.routing.http import routers

    method = get_bound_method_by_http_method_name(routers, web_method)
    route = method(PATH, **handler_kwargs)(handler)

    app = web.Application(http_route_handlers=[route])

    return app


def create_app_use_rapidy_router_as_handler(
        handler: Any,
        web_method: str,
        **handler_kwargs: Any,
) -> web.Application:
    from rapidy.routing.http import routers
    method = get_bound_method_by_http_method_name(routers, web_method)
    app = web.Application(http_route_handlers=[method.handler(PATH, handler, **handler_kwargs)])
    return app


def create_all_type_apps(
        handler: Any,
        web_method: str,
        **handler_kwargs: Any,
) -> Tuple[web.Application, ...]:
    return (
        create_app_use_route_table_def(handler, web_method, **handler_kwargs),
        create_app_use_simple_method_func(handler, web_method, **handler_kwargs),
        create_app_use_app_router(handler, web_method, **handler_kwargs),
        create_app_use_rapidy_router(handler, web_method, **handler_kwargs),
        create_app_use_rapidy_router_as_handler(handler, web_method, **handler_kwargs),
    )


def create_all_function_handler_apps(
        handler_return_type: Any,
        web_method: str,
        return_value: Any,
        **handler_kwargs: Any,
) -> Tuple[web.Application, ...]:
    async def handler() -> handler_return_type:
        return return_value

    return create_all_type_apps(handler, web_method, **handler_kwargs)


def create_all_view_handler_apps(
        handler_return_type: Any,
        web_method: str,
        return_value: Any,
        **handler_kwargs: Any,
) -> Tuple[web.Application, ...]:
    class Handler(web.View):
        async def get(self) -> handler_return_type: return return_value
        async def post(self) -> handler_return_type: return return_value
        async def put(self) -> handler_return_type: return return_value
        async def patch(self) -> handler_return_type: return return_value
        async def delete(self) -> handler_return_type: return return_value
        async def options(self) -> handler_return_type: return return_value

    app_with_routes_as_method = create_all_type_apps(Handler, web_method, **handler_kwargs)
    app_with_routes_as_view = create_all_type_apps(Handler, 'view', **handler_kwargs)
    return *app_with_routes_as_method, *app_with_routes_as_view


def create_middleware_handler_apps(
        handler_return_type: Any,
        web_method: str,
        return_value: Any,
        **handler_kwargs: Any,
) -> Tuple[web.Application, ...]:
    async def handler(): pass

    @web.middleware(**handler_kwargs)
    async def middleware(request: web.Request, handler: Callable[[Any], Awaitable[Any]]) -> handler_return_type:
        return return_value

    method = get_bound_method_by_http_method_name(web, web_method)

    application = web.Application(middlewares=[middleware])
    application.add_routes([method(PATH, handler)])

    return (application,)


app_fabrics: Tuple[AppFabric, ...] = (
    create_all_function_handler_apps,
    create_all_view_handler_apps,
    create_middleware_handler_apps,
)


async def check_fabric(
        app_fabric: AppFabric,
        web_method_name: str,
        *,
        aiohttp_client: AiohttpClient,
        aiohttp_client_response_body_attr_name: Literal['text', 'json', 'read'] = 'json',
        handler_return_type: Any,
        handler_return_value: Optional[Any] = None,
        expected_return_value: Any = DEFAULT_RETURN_VALUE,
        expected_validation_error: bool = False,
        **handler_kwargs: Any,
) -> None:
    all_app_types = app_fabric(handler_return_type, web_method_name, handler_return_value, **handler_kwargs)
    for app in all_app_types:
        client = await aiohttp_client(app)
        client_method = get_bound_method_by_http_method_name(client, web_method_name)

        resp = await client_method(PATH)

        if expected_validation_error:
            assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR
        else:
            assert resp.status == HTTPStatus.OK
            if handler_return_value is not None:
                resp_data = await getattr(resp, aiohttp_client_response_body_attr_name)()
                assert resp_data == expected_return_value


async def check_all_handlers(
        aiohttp_client: AiohttpClient,
        *,
        aiohttp_client_response_body_attr_name: Literal['text', 'json', 'read'] = 'json',
        handler_return_type: Any = inspect.Signature.empty,
        handler_return_value: Optional[Any] = None,
        expected_return_value: Any = DEFAULT_RETURN_VALUE,
        expected_validation_error: bool = False,
        **handler_kwargs: Any,
) -> None:
    for web_method_name in WEB_METHOD_NAMES:
        for app_fabric in app_fabrics:
            await check_fabric(
                aiohttp_client_response_body_attr_name=aiohttp_client_response_body_attr_name,
                app_fabric=app_fabric,
                web_method_name=web_method_name,
                aiohttp_client=aiohttp_client,
                handler_return_type=handler_return_type,
                handler_return_value=handler_return_value,
                expected_return_value=expected_return_value,
                expected_validation_error=expected_validation_error,
                **handler_kwargs,
            )


async def check_all_handlers_with_all_response_model_flows(
        aiohttp_client: AiohttpClient,
        *,
        aiohttp_client_response_body_attr_name: Literal['text', 'json', 'read'] = 'json',
        handler_return_type: Any,
        handler_return_value: Optional[Any] = None,
        expected_return_value: Any = DEFAULT_RETURN_VALUE,
        expected_validation_error: bool = False,
        **handler_kwargs: Any,
) -> None:
    attrs = ['handler_return_type', 'response_type']
    for attr_name in attrs:
        await check_all_handlers(
            aiohttp_client=aiohttp_client,
            aiohttp_client_response_body_attr_name=aiohttp_client_response_body_attr_name,
            handler_return_value=handler_return_value,
            expected_return_value=expected_return_value,
            expected_validation_error=expected_validation_error,
            **handler_kwargs,
            **{attr_name: handler_return_type},
        )
