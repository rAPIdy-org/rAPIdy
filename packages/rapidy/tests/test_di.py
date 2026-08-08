from __future__ import annotations

import asyncio
import inspect
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
import rapidy_core.di as core_di

import rapidy.di as server_di
from rapidy import depends, Rapidy
from rapidy.depends import FromDI, make_async_container, provide, Provider, RapidyProvider, Scope
from rapidy.http import get, Request, Response
from rapidy.typedefs import Send

PUBLIC_DEPENDS = [
    'DEFAULT_COMPONENT',
    'STRICT_VALIDATION',
    'AnyOf',
    'AsyncContainer',
    'BaseScope',
    'Component',
    'Container',
    'FromDI',
    'DependencyKey',
    'Provider',
    'FromComponent',
    'Scope',
    'ValidationSettings',
    'WithParents',
    'alias',
    'decorate',
    'from_context',
    'make_async_container',
    'make_container',
    'new_scope',
    'provide',
    'provide_all',
]
CORE_DEPENDS = [*PUBLIC_DEPENDS, 'wrap_injection']


class RequestResource:
    pass


class AppResource:
    def __init__(self, number: int) -> None:
        self.number = number


class RequestLifecycleProvider(Provider):
    def __init__(self, events: list[str]) -> None:
        super().__init__()
        self.events = events

    @provide(scope=Scope.REQUEST)
    async def resource(self) -> AsyncIterator[RequestResource]:
        self.events.append('request_created')
        yield RequestResource()
        self.events.append('request_finalized')


class AppLifecycleProvider(Provider):
    def __init__(self, events: list[str]) -> None:
        super().__init__()
        self.events = events

    @provide(scope=Scope.APP)
    async def resource(self) -> AsyncIterator[AppResource]:
        self.events.append('app_created')
        yield AppResource(self.events.count('app_created'))
        self.events.append('app_finalized')


class TrackedResponse(Response):
    __slots__ = ('events',)

    def __init__(self, events: list[str]) -> None:
        super().__init__('ok')
        self.events = events

    async def _send(self, send: Send, *, server_info: str | None = None) -> None:
        await super()._send(send, server_info=server_info)
        self.events.append('response_sent')


async def request(app: Rapidy, path: str = '/', *, headers: dict[str, str] | None = None) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url='http://testserver',
    ) as client:
        return await client.get(path, headers=headers)


def test_depends_exact_public_surface_and_core_identity() -> None:
    assert depends.__all__ == PUBLIC_DEPENDS
    assert core_di.FromDI is depends.FromDI
    for name in CORE_DEPENDS:
        assert getattr(depends, name) is getattr(core_di, name)

    assert depends.inject_http is not None
    assert depends.RapidyProvider is RapidyProvider
    for removed in ('CONTAINER_KEY', 'di_middleware', 'inject', 'RapidApiProvider'):
        assert not hasattr(depends, removed)


def test_server_di_source_has_no_legacy_transport_policy() -> None:
    source = inspect.getsource(depends) + inspect.getsource(server_di)
    for removed in (
        'AIOHTTP_VERSION_TUPLE',
        'AppKey',
        'CONTAINER_KEY',
        'ConnectionHeader',
        'UpgradeHeader',
        'RapidApiProvider',
        'di_middleware',
    ):
        assert removed not in source


@pytest.mark.asyncio
async def test_request_dependency_resolves_once_and_finalizes_after_response_send() -> None:
    events: list[str] = []

    @get('/')
    async def handler(first: FromDI[RequestResource], second: FromDI[RequestResource]) -> Response:
        assert first is second
        events.append('handler')
        return TrackedResponse(events)

    app = Rapidy(di_providers=[RequestLifecycleProvider(events)], http_route_handlers=[handler])
    async with app.lifespan.ctx_manager():
        response = await request(app)

    assert response.status_code == 200
    assert response.text == 'ok'
    assert events == ['request_created', 'handler', 'response_sent', 'request_finalized']


@pytest.mark.asyncio
async def test_inject_http_preserves_legacy_implicit_request_parameter() -> None:
    events: list[str] = []

    @get('/')
    async def handler(current_request, resource: FromDI[RequestResource]) -> str:
        assert isinstance(current_request, Request)
        assert resource is not None
        return 'ok'

    app = Rapidy(di_providers=[RequestLifecycleProvider(events)], http_route_handlers=[handler])
    async with app.lifespan.ctx_manager():
        response = await request(app)

    assert response.text == 'ok'
    assert events == ['request_created', 'request_finalized']


@pytest.mark.asyncio
async def test_request_finalizer_runs_for_handler_exception_and_cancellation() -> None:
    exception_events: list[str] = []

    @get('/exception')
    async def exception_handler(resource: FromDI[RequestResource]) -> None:
        assert resource is not None
        exception_events.append('handler')
        raise RuntimeError('expected')

    exception_app = Rapidy(
        di_providers=[RequestLifecycleProvider(exception_events)],
        http_route_handlers=[exception_handler],
    )
    async with exception_app.lifespan.ctx_manager():
        response = await request(exception_app, '/exception')

    assert response.status_code == 500
    assert exception_events == ['request_created', 'handler', 'request_finalized']

    cancellation_events: list[str] = []

    @get('/cancel')
    async def cancellation_handler(resource: FromDI[RequestResource]) -> None:
        assert resource is not None
        cancellation_events.append('handler')
        raise asyncio.CancelledError

    cancellation_app = Rapidy(
        di_providers=[RequestLifecycleProvider(cancellation_events)],
        http_route_handlers=[cancellation_handler],
    )

    async def receive() -> dict[str, Any]:
        return {'type': 'http.request', 'body': b'', 'more_body': False}

    async def send(_message: dict[str, Any]) -> None:
        return None

    scope: dict[str, Any] = {
        'type': 'http',
        'method': 'GET',
        'path': '/cancel',
        'headers': [],
        'query_string': b'',
    }
    async with cancellation_app.lifespan.ctx_manager():
        with pytest.raises(asyncio.CancelledError):
            await cancellation_app(scope, receive, send)

    assert cancellation_events == ['request_created', 'handler', 'request_finalized']


@pytest.mark.asyncio
async def test_app_singleton_and_owned_container_close_once() -> None:
    events: list[str] = []

    async def cleanup() -> None:
        events.append('cleanup')

    @get('/')
    async def handler(resource: FromDI[AppResource]) -> str:
        return str(resource.number)

    app = Rapidy(
        di_providers=[AppLifecycleProvider(events)],
        http_route_handlers=[handler],
        on_cleanup=[cleanup],
    )
    assert app.di_container is None
    async with app.lifespan.ctx_manager():
        container = app.di_container
        assert container is not None
        first = await request(app)
        second = await request(app)
        assert app.di_container is container

    assert first.text == second.text == '1'
    assert events == ['app_created', 'app_finalized', 'cleanup']


@pytest.mark.asyncio
async def test_external_container_is_not_closed_by_application() -> None:
    events: list[str] = []
    external_container = make_async_container(AppLifecycleProvider(events))

    @get('/')
    async def handler(resource: FromDI[AppResource]) -> str:
        return str(resource.number)

    app = Rapidy(di_container=external_container, http_route_handlers=[handler])
    async with app.lifespan.ctx_manager():
        assert app.di_container is external_container
        response = await request(app)

    assert response.text == '1'
    assert events == ['app_created']
    await external_container.close()
    assert events == ['app_created', 'app_finalized']


@pytest.mark.asyncio
async def test_session_request_binding_resolves_from_direct_request_entry() -> None:
    app = Rapidy()
    async with app.lifespan.ctx_manager():
        container = app.di_container
        assert container is not None
        scope: dict[str, Any] = {
            'type': 'http',
            'method': 'GET',
            'path': '/',
            'headers': [],
            'query_string': b'',
            'app': app,
        }

        async def receive() -> dict[str, Any]:
            return {'type': 'http.request', 'body': b'', 'more_body': False}

        current_request = Request(scope, receive)
        async with container(context={Request: current_request}, scope=Scope.REQUEST) as request_container:
            assert await request_container.get(Request) is current_request


@pytest.mark.asyncio
async def test_http_headers_do_not_change_request_scope() -> None:
    events: list[str] = []

    @get('/')
    async def handler(resource: FromDI[RequestResource]) -> str:
        assert resource is not None
        return 'ok'

    app = Rapidy(di_providers=[RequestLifecycleProvider(events)], http_route_handlers=[handler])
    async with app.lifespan.ctx_manager():
        response = await request(app, headers={'upgrade': 'websocket', 'connection': 'Upgrade'})

    assert response.text == 'ok'
    assert events == ['request_created', 'request_finalized']


@pytest.mark.asyncio
async def test_mounted_child_uses_root_scope_but_exposes_no_container() -> None:
    events: list[str] = []

    @get('/')
    async def handler(resource: FromDI[AppResource]) -> str:
        return str(resource.number)

    root = Rapidy(di_providers=[AppLifecycleProvider(events)])
    child = Rapidy(http_route_handlers=[handler])
    child._bind_to_root(root)

    async with root.lifespan.ctx_manager(), child.lifespan.ctx_manager():
        assert root.di_container is not None
        assert child.di_container is None
        response = await request(child)

    assert response.text == '1'
    assert events == ['app_created', 'app_finalized']
