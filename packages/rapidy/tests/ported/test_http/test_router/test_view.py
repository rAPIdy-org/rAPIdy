from __future__ import annotations

from rapidy_core.enums import ContentType

from rapidy import Rapidy
from rapidy.http import controller
from rapidy.typedefs import View
from tests.ported.client import AppClientFactory


async def test_allow_head(app_client: AppClientFactory) -> None:
    class FooView(View):
        async def get(self) -> None:
            return None

    app = Rapidy(http_route_handlers=[controller.reg('/test', FooView)])
    client = await app_client(app)

    resp = await client.get('/test')
    assert resp.status == 200

    resp = await client.head('/test')
    assert resp.status == 200


async def test_method_not_exists(app_client: AppClientFactory) -> None:
    class FooView(View):
        async def get(self) -> None:
            return None

    app = Rapidy(http_route_handlers=[controller.reg('/test', FooView)])
    client = await app_client(app)

    response = await client.post('/test')
    assert response.status == 405


async def test_different_attr_def(app_client: AppClientFactory) -> None:
    class FooView(View):
        async def get(self) -> None:
            return None

        async def post(self) -> None:
            return None

    app = Rapidy(
        http_route_handlers=[
            controller.reg('/test/1', FooView, response_content_type=ContentType.text_plain),
            controller.reg('/test/2', FooView, response_content_type=ContentType.text_html),
        ]
    )

    client = await app_client(app)

    resp = await client.get('/test/1')
    assert resp.status == 200
    assert resp.headers['Content-Type'].startswith('text/plain')

    resp = await client.get('/test/2')
    assert resp.status == 200
    assert resp.headers['Content-Type'].startswith('text/html')
