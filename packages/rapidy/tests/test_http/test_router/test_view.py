import pytest
from aiohttp.pytest_plugin import AiohttpClient

from rapidy import web
from rapidy.endpoint_handlers.http.handlers import MethodNotFoundInViewError
from rapidy.enums import ContentType


async def test_allow_head(aiohttp_client: AiohttpClient) -> None:
    class FooView(web.View):
        async def get(self) -> None:
            return None

    app = web.Application()

    app.router.add_get('/test', FooView)
    client = await aiohttp_client(app)

    resp = await client.get('/test')
    assert resp.status == 200

    resp = await client.head('/test')
    assert resp.status == 200


async def test_method_not_exists() -> None:
    class FooView(web.View):
        async def get(self) -> None:
            return None

    app = web.Application()

    with pytest.raises(MethodNotFoundInViewError):
        app.router.add_post('/test', FooView)


async def test_different_attr_def(aiohttp_client: AiohttpClient) -> None:
    class FooView(web.View):
        async def get(self) -> None:
            return None

        async def post(self) -> None:
            return None

    app = web.Application()
    app.router.add_get('/test/1', FooView, response_content_type=ContentType.text_plain)
    app.router.add_get('/test/2', FooView, response_content_type=ContentType.text_html)

    client = await aiohttp_client(app)

    resp = await client.get('/test/1')
    assert resp.status == 200
    assert resp.headers['Content-Type'].startswith('text/plain')

    resp = await client.get('/test/2')
    assert resp.status == 200
    assert resp.headers['Content-Type'].startswith('text/html')
