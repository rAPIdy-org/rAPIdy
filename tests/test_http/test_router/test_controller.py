import pytest
from aiohttp.pytest_plugin import AiohttpClient

from rapidy import Rapidy
from rapidy.enums import ContentType, MethodName
from rapidy.http import controller, delete, get, head, options, patch, PathParam, post, put
from rapidy.routing.http.base import IncorrectPathError, RouterTypeError
from tests.test_http.test_router.helpers import parametrize_method_names


@parametrize_method_names
async def test_register_all_methods(
    aiohttp_client: AiohttpClient,
    method_name: MethodName,
) -> None:
    @controller('/test')
    class Controller:
        @get(allow_head=False)
        async def get(self) -> None:
            pass

        @post()
        async def post(self) -> None:
            pass

        @put()
        async def put(self) -> None:
            pass

        @patch()
        async def patch(self) -> None:
            pass

        @delete()
        async def delete(self) -> None:
            pass

        @head()
        async def head(self) -> None:
            pass

        @options()
        async def options(self) -> None:
            pass

    app = Rapidy(http_route_handlers=[Controller])
    client = await aiohttp_client(app)

    resp = await getattr(client, method_name)('/test')
    assert resp.status == 200


async def test_head_already_registered() -> None:
    @controller('/test')
    class Controller:
        @get()
        async def get(self) -> None:
            pass

        @head()
        async def head(self) -> None:
            pass

    with pytest.raises(RuntimeError):
        Rapidy(http_route_handlers=[Controller])


@parametrize_method_names
async def test_path(
    aiohttp_client: AiohttpClient,
    method_name: MethodName,
) -> None:
    @controller('/test/{foo}')
    class Controller:
        @get(allow_head=False)
        async def get_one(self, foo: str = PathParam()) -> None:
            pass

        @post()
        async def post(self, foo: str = PathParam()) -> None:
            pass

        @put()
        async def put(self, foo: str = PathParam()) -> None:
            pass

        @patch()
        async def patch(self, foo: str = PathParam()) -> None:
            pass

        @delete()
        async def delete(self, foo: str = PathParam()) -> None:
            pass

        @head()
        async def head(self, foo: str = PathParam()) -> None:
            pass

        @options()
        async def options(self, foo: str = PathParam()) -> None:
            pass

    app = Rapidy(http_route_handlers=[Controller])
    client = await aiohttp_client(app)

    resp = await getattr(client, method_name)('/test/foo')
    assert resp.status == 200


async def test_double_get(aiohttp_client: AiohttpClient) -> None:
    @controller('/test')
    class Controller:
        @get('/{foo}')
        async def get_one(self, foo: str = PathParam()) -> None:
            pass

        @get()
        async def get(self) -> None:
            pass

    app = Rapidy(http_route_handlers=[Controller])
    client = await aiohttp_client(app)

    resp = await client.get('/test/1')
    assert resp.status == 200

    resp = await client.get('/test')
    assert resp.status == 200


async def test_def_without_deco(aiohttp_client: AiohttpClient) -> None:
    class Controller:
        @get()
        async def get(self) -> None:
            pass

    app = Rapidy(http_route_handlers=[controller.reg('/test', Controller)])
    client = await aiohttp_client(app)

    resp = await client.get('/test')
    assert resp.status == 200


async def test_inherited_params(aiohttp_client: AiohttpClient) -> None:
    @controller('/test', response_content_type=ContentType.text_plain)
    class Controller:
        @get('/1')
        async def overridden(self) -> dict[str, str]:
            return {}

        @get('/2', response_content_type=ContentType.json)
        async def not_overridden(self) -> dict[str, str]:
            return {}

    app = Rapidy(http_route_handlers=[Controller])
    client = await aiohttp_client(app)

    resp = await client.get('/test/1')
    assert resp.status == 200
    assert resp.headers['Content-Type'].startswith('text/plain')

    resp = await client.get('/test/2')
    assert resp.status == 200
    assert resp.headers['Content-Type'].startswith('application/json')


async def test_missing_view_deco() -> None:
    class IncorrectController:
        @get('/test')
        async def get_one(self) -> None:
            pass

    with pytest.raises(RouterTypeError):
        Rapidy(http_route_handlers=[IncorrectController])


async def test_path_empty() -> None:
    with pytest.raises(IncorrectPathError):

        @controller('')
        class Controller:
            @get()
            async def get(self) -> None:
                pass


async def test_instance(aiohttp_client: AiohttpClient) -> None:
    @controller('/')
    class Controller:
        def __init__(self) -> None:
            self.foo = True

        @get()
        async def get(self) -> None:
            assert self.foo

    app = Rapidy(http_route_handlers=[Controller])
    client = await aiohttp_client(app)

    resp = await client.get('/')
    assert resp.status == 200
