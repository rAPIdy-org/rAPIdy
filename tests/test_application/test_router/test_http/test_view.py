import pytest
from aiohttp.pytest_plugin import AiohttpClient
from aiohttp.web_urldispatcher import View

from rapidy import web
from rapidy._base_exceptions import RapidyException
from rapidy.enums import MethodName
from rapidy.routing.http.routers import get, IncorrectTypeViewError, view
from tests.test_application.test_router.test_http.helpers import parametrize_method_names


@parametrize_method_names
async def test_simple(
        aiohttp_client: AiohttpClient,
        method_name: MethodName,
) -> None:
    @view('/test')
    class FooView(View):
        async def get(self) -> None: pass
        async def post(self) -> None: pass
        async def put(self) -> None: pass
        async def patch(self) -> None: pass
        async def delete(self) -> None: pass
        async def head(self) -> None: pass
        async def options(self) -> None: pass

    app = web.Application(http_route_handlers=[FooView])
    client = await aiohttp_client(app)

    resp = await getattr(client, method_name)('/test')
    assert resp.status == 200


@parametrize_method_names
async def test_path(
        aiohttp_client: AiohttpClient,
        method_name: MethodName,
) -> None:
    @view('/test/{foo}')
    class FooView(View):
        async def get(self, foo: str = web.PathParam()) -> None: pass
        async def post(self, foo: str = web.PathParam()) -> None: pass
        async def put(self, foo: str = web.PathParam()) -> None: pass
        async def patch(self, foo: str = web.PathParam()) -> None: pass
        async def delete(self, foo: str = web.PathParam()) -> None: pass
        async def head(self, foo: str = web.PathParam()) -> None: pass
        async def options(self, foo: str = web.PathParam()) -> None: pass

    app = web.Application(http_route_handlers=[FooView])
    client = await aiohttp_client(app)

    resp = await getattr(client, method_name)('/test/foo')
    assert resp.status == 200


async def test_double_get1(aiohttp_client: AiohttpClient) -> None:
    @view('/test')
    class FooView(View):
        @get('/test/{foo}')
        async def get_one(self, foo: str = web.PathParam()) -> None: pass
        async def get(self) -> None: pass
        async def post(self) -> None: pass

    app = web.Application(http_route_handlers=[FooView])
    client = await aiohttp_client(app)

    resp = await client.get('/test/foo')
    assert resp.status == 200

    resp = await client.get('/test')
    assert resp.status == 200

    resp = await client.post('/test')
    assert resp.status == 200


async def test_double_get2(aiohttp_client: AiohttpClient) -> None:
    @view('/test')
    class FooView(View):
        @get('/test/{foo}')
        async def get_one(self, foo: str = web.PathParam()) -> None: pass
        @get('/test')
        async def get_all(self) -> None: pass
        async def post(self) -> None: pass

    app = web.Application(http_route_handlers=[FooView])
    client = await aiohttp_client(app)

    resp = await client.get('/test/foo')
    assert resp.status == 200

    resp = await client.get('/test')
    assert resp.status == 200

    resp = await client.post('/test')
    assert resp.status == 200


async def test_missing_view_deco() -> None:
    class FooView(View):
        @get('/test/{foo}')
        async def get_one(self, foo: str = web.PathParam()) -> None: pass

    with pytest.raises(RapidyException):
        web.Application(http_route_handlers=[FooView])


async def test_incorrect_view() -> None:
    with pytest.raises(IncorrectTypeViewError):
        @view('/test')
        async def get_one() -> None: pass
