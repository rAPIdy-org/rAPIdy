from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
import pytest

from rapidy import Rapidy
from rapidy.depends import AsyncContainer, FromDI, provide, Provider, Scope
from rapidy.http import get, post, Request, Response
from rapidy.routing.http.routers import HTTPRouter
from rapidy.typedefs import CallNext, Middleware, Send


async def request(app: Rapidy, method: str, path: str, **kwargs: Any) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url='http://testserver',
    ) as client:
        return await client.request(method, path, **kwargs)


@pytest.mark.asyncio
async def test_httprouter_v1() -> None:
    events: list[str] = []

    async def root_middleware(current_request: Request, call_next: CallNext) -> Response:
        events.append('root')
        return await call_next(current_request)

    async def subapp_middleware(current_request: Request, call_next: CallNext) -> Response:
        events.append('subapp')
        return await call_next(current_request)

    async def subapp_startup() -> None:
        events.append('subapp_startup')

    @get('/item')
    async def child_handler() -> str:
        return 'child'

    @get('/root')
    async def root_handler() -> str:
        return 'root'

    router = HTTPRouter(
        '/v1',
        [child_handler],
        middlewares=[subapp_middleware],
        client_max_size=1024,
        on_startup=[subapp_startup],
    )
    app = Rapidy(middlewares=[root_middleware], http_route_handlers=[router, root_handler])

    async with app.lifespan.ctx_manager():
        assert events == ['subapp_startup']
        child_response = await request(app, 'GET', '/v1/item')
        assert events[-2:] == ['root', 'subapp']
        root_response = await request(app, 'GET', '/root')
        assert events[-1] == 'root'

    assert child_response.text == 'child'
    assert root_response.text == 'root'
    assert events.count('subapp') == 1


@pytest.mark.asyncio
async def test_subapp_client_max_size() -> None:
    async def body_handler(current_request: Request) -> str:
        return str(len(await current_request.read()))

    router = HTTPRouter('/v1', [post.reg('/body', body_handler)], client_max_size=1024)
    app = Rapidy(http_route_handlers=[router, post.reg('/body', body_handler)])
    payload = b'x' * 2048

    async with app.lifespan.ctx_manager():
        child_response = await request(app, 'POST', '/v1/body', content=payload)
        root_response = await request(app, 'POST', '/body', content=payload)

    assert child_response.status_code == 413
    assert root_response.status_code == 200
    assert root_response.text == '2048'


@pytest.mark.asyncio
async def test_request_app_rebound() -> None:
    seen: list[Rapidy] = []

    @get('/where')
    async def child_handler(current_request: Request) -> str:
        seen.append(current_request.app)
        return 'child'

    @get('/where')
    async def root_handler(current_request: Request) -> str:
        seen.append(current_request.app)
        return 'root'

    router = HTTPRouter('/v1', [child_handler])
    app = Rapidy(http_route_handlers=[router, root_handler])
    async with app.lifespan.ctx_manager():
        await request(app, 'GET', '/where')
        await request(app, 'GET', '/v1/where')

    assert seen == [app, router.application]


@pytest.mark.asyncio
async def test_recursive_mount() -> None:
    events: list[str] = []

    def make_middleware(name: str) -> Middleware:
        async def current_middleware(current_request: Request, call_next: CallNext) -> Response:
            events.append(name)
            return await call_next(current_request)

        return current_middleware

    @get('/item')
    async def handler() -> str:
        events.append('handler')
        return 'nested'

    admin = HTTPRouter('/admin', [handler], middlewares=[make_middleware('admin')])
    api = HTTPRouter('/v1', [admin], middlewares=[make_middleware('v1')])
    app = Rapidy(middlewares=[make_middleware('root')], http_route_handlers=[api])

    async with app.lifespan.ctx_manager():
        response = await request(app, 'GET', '/v1/admin/item')

    assert response.text == 'nested'
    assert events == ['root', 'v1', 'admin', 'handler']


@pytest.mark.asyncio
async def test_subapp_di_container_is_none() -> None:
    router = HTTPRouter('/v1')
    app = Rapidy(http_route_handlers=[router])
    async with app.lifespan.ctx_manager():
        assert isinstance(app.di_container, AsyncContainer)
        assert router.application.di_container is None


class RequestResource:
    pass


class AppResource:
    pass


class ResourceProvider(Provider):
    def __init__(self, events: list[str]) -> None:
        super().__init__()
        self.events = events

    @provide(scope=Scope.REQUEST)
    async def request_resource(self) -> AsyncIterator[RequestResource]:
        self.events.append('request_created')
        yield RequestResource()
        self.events.append('request_finalized')

    @provide(scope=Scope.APP)
    def app_resource(self) -> AppResource:
        self.events.append('app_created')
        return AppResource()


class TrackedResponse(Response):
    __slots__ = ('events',)

    def __init__(self, events: list[str]) -> None:
        super().__init__('ok')
        self.events = events

    async def _send(self, send: Send, *, server_info: str | None = None) -> None:
        await super()._send(send, server_info=server_info)
        self.events.append('response_sent')


@pytest.mark.asyncio
async def test_di_resolve_in_subapp() -> None:
    events: list[str] = []
    app_instances: list[AppResource] = []

    async def handler(request_resource: FromDI[RequestResource], app_resource: FromDI[AppResource]) -> Response:
        assert request_resource is not None
        app_instances.append(app_resource)
        events.append('handler')
        return TrackedResponse(events)

    router = HTTPRouter('/v1', [get.reg('/resource', handler)])
    app = Rapidy(
        di_providers=[ResourceProvider(events)],
        http_route_handlers=[get.reg('/resource', handler), router],
    )
    async with app.lifespan.ctx_manager():
        first = await request(app, 'GET', '/resource')
        second = await request(app, 'GET', '/v1/resource')

    assert first.text == second.text == 'ok'
    assert app_instances[0] is app_instances[1]
    assert events.count('app_created') == 1
    assert [event for event in events if event != 'app_created'] == [
        'request_created',
        'handler',
        'response_sent',
        'request_finalized',
        'request_created',
        'handler',
        'response_sent',
        'request_finalized',
    ]


@pytest.mark.asyncio
async def test_di_scope_covers_subapp_middleware() -> None:
    events: list[str] = []
    seen: list[bool] = []

    async def inspect_scope(current_request: Request, call_next: CallNext) -> Response:
        container = current_request.state.di_container
        resource = await container.get(RequestResource)
        seen.append(isinstance(resource, RequestResource))
        return await call_next(current_request)

    @get('/')
    async def handler() -> str:
        return 'ok'

    router = HTTPRouter('/v1', [handler], middlewares=[inspect_scope])
    app = Rapidy(di_providers=[ResourceProvider(events)], http_route_handlers=[router])
    async with app.lifespan.ctx_manager():
        response = await request(app, 'GET', '/v1/')

    assert response.text == 'ok'
    assert seen == [True]


@pytest.mark.asyncio
async def test_subapp_lifespan_nesting() -> None:
    events: list[str] = []

    @asynccontextmanager
    async def root_context(_app: Rapidy) -> AsyncIterator[None]:
        events.append('root_ctx_enter')
        try:
            yield
        finally:
            events.append('root_ctx_exit')

    @asynccontextmanager
    async def subapp_context(_app: Rapidy) -> AsyncIterator[None]:
        events.append('subapp_ctx_enter')
        try:
            yield
        finally:
            events.append('subapp_ctx_exit')

    async def subapp_shutdown() -> None:
        events.append('subapp_on_shutdown')

    router = HTTPRouter('/v1', lifespan=[subapp_context], on_shutdown=[subapp_shutdown])
    app = Rapidy(lifespan=[root_context], http_route_handlers=[router])

    async with app.lifespan.ctx_manager():
        events.append('work')

    assert events == [
        'root_ctx_enter',
        'subapp_ctx_enter',
        'work',
        'subapp_on_shutdown',
        'subapp_ctx_exit',
        'root_ctx_exit',
    ]


def test_root_routes_include_subapp() -> None:
    @get('/item')
    async def handler() -> str:
        return 'ok'

    app = Rapidy(http_route_handlers=[HTTPRouter('/v1', [HTTPRouter('/admin', [handler])])])
    assert {record.path for record in app.routes} == {'/v1/admin/item'}


@pytest.mark.asyncio
async def test_mount_validation_and_mutation_after_startup() -> None:
    app = Rapidy()
    for prefix in ('v1', '/', '/v1/'):
        with pytest.raises(ValueError, match='prefix'):
            app.add_subapp(prefix, Rapidy())

    async with app.lifespan.ctx_manager():
        with pytest.raises(RuntimeError, match='after application startup'):
            app.add_subapp('/v1', Rapidy())
