from typing import Any, Final

from aiohttp.pytest_plugin import AiohttpClient
from dishka import FromDishka, make_async_container, provide, Provider, Scope

from rapidy import Rapidy
from rapidy.http import controller, get, Request, StreamResponse
from rapidy.routing.http.routers import HTTPRouter
from rapidy.typedefs import CallNext
from rapidy.web import View
from rapidy.web_middlewares import middleware

DEFAULT: Final[int] = 1


class FooProvider(Provider):
    scope = Scope.REQUEST

    @provide
    async def c(self) -> int:
        return DEFAULT


async def test_route(aiohttp_client: AiohttpClient) -> None:
    @get('/')
    async def handler(c: FromDishka[int]) -> Any:
        assert c == DEFAULT

    app = Rapidy(http_route_handlers=[handler], di_providers=[FooProvider()])

    client = await aiohttp_client(app)
    resp = await client.get('/')

    assert resp.status == 200


async def test_router(aiohttp_client: AiohttpClient) -> None:
    @get('/')
    async def handler(c: FromDishka[int]) -> Any:
        assert c == DEFAULT

    router = HTTPRouter('/foo', route_handlers=[handler])

    app = Rapidy(http_route_handlers=[router], di_providers=[FooProvider()])

    client = await aiohttp_client(app)
    resp = await client.get('/foo/')

    assert resp.status == 200
    assert app.di_container


async def test_subapp(aiohttp_client: AiohttpClient) -> None:
    @get('/')
    async def handler(c: FromDishka[int]) -> Any:
        assert c == DEFAULT

    subapp = Rapidy(http_route_handlers=[handler])

    app = Rapidy(di_providers=[FooProvider()])
    app.add_subapp('/foo', subapp)

    client = await aiohttp_client(app)
    resp = await client.get('/foo/')

    assert resp.status == 200
    assert app.di_container
    assert subapp.di_container is None


async def test_already_exists_container(aiohttp_client: AiohttpClient) -> None:
    container = make_async_container(FooProvider())

    @get('/')
    async def handler(c: FromDishka[int]) -> Any:
        assert c == DEFAULT

    app = Rapidy(di_container=container, http_route_handlers=[handler])

    client = await aiohttp_client(app)
    resp = await client.get('/')

    assert resp.status == 200
    assert app.di_container


async def test_controller(aiohttp_client: AiohttpClient) -> None:
    @controller('/')
    class Controller:
        @get()
        async def handler(self, c: FromDishka[int]) -> Any:
            assert c == DEFAULT

    app = Rapidy(http_route_handlers=[Controller], di_providers=[FooProvider()])

    client = await aiohttp_client(app)
    resp = await client.get('/')

    assert resp.status == 200


async def test_view(aiohttp_client: AiohttpClient) -> None:
    class Foo(View):
        def __init__(self, request: Request) -> None:
            super().__init__(request)

        async def get(self, c: FromDishka[int]) -> Any:
            assert c == DEFAULT

    app = Rapidy(di_providers=[FooProvider()])

    app.router.add_view('/', Foo)

    client = await aiohttp_client(app)
    resp = await client.get('/')

    assert resp.status == 200


async def test_aiohttp_func_handler(aiohttp_client: AiohttpClient) -> None:
    async def get(c: FromDishka[int]) -> Any:
        assert c == DEFAULT

    app = Rapidy(di_providers=[FooProvider()])
    app.router.add_get('/', get)

    client = await aiohttp_client(app)
    resp = await client.get('/')

    assert resp.status == 200


async def test_fst_param_annotation_empty(aiohttp_client: AiohttpClient) -> None:
    async def get(empty, c: FromDishka[int]) -> Any:  # type: ignore[no-untyped-def]
        assert c == DEFAULT

    app = Rapidy(di_providers=[FooProvider()])

    app.router.add_get('/', get)

    client = await aiohttp_client(app)
    resp = await client.get('/')

    assert resp.status == 200


async def test_middleware(aiohttp_client: AiohttpClient) -> None:
    @middleware
    async def simple_middleware(
        request: Request,
        call_next: CallNext,
        c: FromDishka[int],
    ) -> StreamResponse:
        assert c == DEFAULT
        return await call_next(request)

    @get('/')
    async def handler(c: FromDishka[int]) -> Any:
        assert c == DEFAULT

    app = Rapidy(
        di_providers=[FooProvider()],
        middlewares=[simple_middleware],
        http_route_handlers=[handler],
    )

    client = await aiohttp_client(app)
    resp = await client.get('/')

    assert resp.status == 200
