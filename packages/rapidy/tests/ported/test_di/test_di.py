from __future__ import annotations

from typing import Any, Final

from rapidy import Rapidy
from rapidy.depends import FromDI, make_async_container, provide, Provider, Scope
from rapidy.http import controller, get, middleware, Request, Response
from rapidy.routing.http.routers import HTTPRouter
from rapidy.typedefs import CallNext, View
from tests.ported.client import AppClientFactory

DEFAULT: Final[int] = 1


class FooProvider(Provider):
    scope = Scope.REQUEST

    @provide
    async def c(self) -> int:
        return DEFAULT


async def test_route(app_client: AppClientFactory) -> None:
    @get('/')
    async def handler(c: FromDI[int]) -> Any:
        assert c == DEFAULT

    app = Rapidy(http_route_handlers=[handler], di_providers=[FooProvider()])
    client = await app_client(app)
    response = await client.get('/')
    assert response.status == 200


async def test_router(app_client: AppClientFactory) -> None:
    @get('/')
    async def handler(c: FromDI[int]) -> Any:
        assert c == DEFAULT

    router = HTTPRouter('/foo', route_handlers=[handler])
    app = Rapidy(http_route_handlers=[router], di_providers=[FooProvider()])
    client = await app_client(app)
    response = await client.get('/foo/')
    assert response.status == 200
    assert app.di_container


async def test_subapp(app_client: AppClientFactory) -> None:
    @get('/')
    async def handler(c: FromDI[int]) -> Any:
        assert c == DEFAULT

    subapp = Rapidy(http_route_handlers=[handler])
    app = Rapidy(di_providers=[FooProvider()])
    app.add_subapp('/foo', subapp)
    client = await app_client(app)
    response = await client.get('/foo/')
    assert response.status == 200
    assert app.di_container
    assert subapp.di_container is None


async def test_already_exists_container(app_client: AppClientFactory) -> None:
    container = make_async_container(FooProvider())

    @get('/')
    async def handler(c: FromDI[int]) -> Any:
        assert c == DEFAULT

    app = Rapidy(di_container=container, http_route_handlers=[handler])
    client = await app_client(app)
    response = await client.get('/')
    assert response.status == 200
    assert app.di_container is container
    await client.close()
    await container.close()


async def test_controller(app_client: AppClientFactory) -> None:
    @controller('/')
    class Controller:
        @get()
        async def handler(self, c: FromDI[int]) -> Any:
            assert c == DEFAULT

    app = Rapidy(http_route_handlers=[Controller], di_providers=[FooProvider()])
    client = await app_client(app)
    response = await client.get('/')
    assert response.status == 200


async def test_view(app_client: AppClientFactory) -> None:
    class Foo(View):
        async def get(self, c: FromDI[int]) -> Any:
            assert c == DEFAULT

    app = Rapidy(
        di_providers=[FooProvider()],
        http_route_handlers=[controller.reg('/', Foo)],
    )
    client = await app_client(app)
    response = await client.get('/')
    assert response.status == 200


async def test_function_handler(app_client: AppClientFactory) -> None:
    async def handler(c: FromDI[int]) -> Any:
        assert c == DEFAULT

    app = Rapidy(
        di_providers=[FooProvider()],
        http_route_handlers=[get.reg('/', handler)],
    )
    client = await app_client(app)
    response = await client.get('/')
    assert response.status == 200


async def test_fst_param_annotation_empty(app_client: AppClientFactory) -> None:
    async def handler(empty, c: FromDI[int]) -> Any:  # type: ignore[no-untyped-def]
        assert c == DEFAULT

    app = Rapidy(
        di_providers=[FooProvider()],
        http_route_handlers=[get.reg('/', handler)],
    )
    client = await app_client(app)
    response = await client.get('/')
    assert response.status == 200


async def test_middleware(app_client: AppClientFactory) -> None:
    @middleware
    async def simple_middleware(
        request: Request,
        call_next: CallNext,
        c: FromDI[int],
    ) -> Response:
        assert c == DEFAULT
        return await call_next(request)

    @get('/')
    async def handler(c: FromDI[int]) -> Any:
        assert c == DEFAULT

    app = Rapidy(
        di_providers=[FooProvider()],
        middlewares=[simple_middleware],
        http_route_handlers=[handler],
    )
    client = await app_client(app)
    response = await client.get('/')
    assert response.status == 200
