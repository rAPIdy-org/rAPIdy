from __future__ import annotations

from http import HTTPStatus
from typing import Any

import httpx
import pytest
from pydantic import BaseModel
from rapidy_core.constants import DEFAULT_JSON_ENCODER
from rapidy_core.enums import Charset, ContentType

from rapidy import Rapidy
from rapidy.endpoint_handlers.http.controller import controller_factory, HandlerController, ResponseValidationError
from rapidy.http import controller, get, HTTPRouter, post, Request, Response
from rapidy.routing.http.routers import HandlerIsNotAsyncFuncTypeError
from rapidy.typedefs import UNSET, View


class Item(BaseModel):
    value: int


async def request(app: Rapidy, method: str = 'GET', path: str = '/') -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url='http://testserver',
    ) as client:
        return await client.request(method, path)


def make_controller(handler: Any, *, response_validate: bool = True) -> HandlerController:
    return controller_factory(
        handler,
        status_code=HTTPStatus.CREATED,
        response_validate=response_validate,
        response_type=UNSET,
        response_content_type=None,
        response_charset=Charset.utf8.value,
        response_zlib_executor=None,
        response_zlib_executor_size=None,
        response_json_encoder=DEFAULT_JSON_ENCODER,
        response_include_fields=None,
        response_exclude_fields=None,
        response_by_alias=True,
        response_exclude_unset=False,
        response_exclude_defaults=False,
        response_exclude_none=False,
        response_custom_encoder=None,
    )


@pytest.mark.asyncio
async def test_create_response_branches() -> None:
    async def handler() -> Any:
        return None

    handler_controller = make_controller(handler)
    ready = Response('ready', status=202)
    assert await handler_controller.create_response(ready, None) is ready

    current = Response(status=203)
    assert await handler_controller.create_response(None, current) is current

    result = await handler_controller.create_response({'value': 1}, current)
    assert result is current
    assert current.text == '{"value": 1}'

    created = await handler_controller.create_response(None, None)
    assert isinstance(created, Response)
    assert created.status == 201

    async def validated() -> int:
        return 1

    with pytest.raises(ResponseValidationError, match='Validation errors'):
        await make_controller(validated).create_response('invalid', None)
    unvalidated = await make_controller(validated, response_validate=False).create_response('invalid', None)
    assert isinstance(unvalidated, Response)
    assert unvalidated.text == 'invalid'


@pytest.mark.asyncio
async def test_response_injection_return_data_and_none() -> None:
    seen: list[tuple[int, str]] = []

    @get('/items', status_code=202, response_content_type=ContentType.json)
    async def items(request: Request, response: Response) -> list[Item]:
        seen.append((response.status, response.content_type))
        response.status = 201
        response.set_cookie('seen', '1')
        response.headers['x-path'] = request.path
        return [Item(value=1)]

    @get('/empty', status_code=202)
    async def empty(response: Response) -> None:
        response.status = 204
        response.headers['x-empty'] = 'yes'
        response.set_cookie('empty', '1')

    app = Rapidy(http_route_handlers=[items, empty])
    async with app.lifespan.ctx_manager():
        item_response = await request(app, path='/items')
        empty_response = await request(app, path='/empty')

    assert seen == [(202, 'application/json')]
    assert item_response.status_code == 201
    assert item_response.json() == [{'value': 1}]
    assert item_response.headers['x-path'] == '/items'
    assert 'seen=1' in item_response.headers['set-cookie']
    assert empty_response.status_code == 204
    assert empty_response.content == b''
    assert empty_response.headers['x-empty'] == 'yes'
    assert 'empty=1' in empty_response.headers['set-cookie']


@pytest.mark.asyncio
async def test_ready_response_replaces_pre_response() -> None:
    @get('/ready', status_code=201, response_content_type=ContentType.json)
    async def handler(response: Response) -> Response:
        response.headers['x-discarded'] = 'yes'
        return Response('ready', status=418, headers={'x-ready': 'yes'})

    app = Rapidy(http_route_handlers=[handler])
    async with app.lifespan.ctx_manager():
        result = await request(app, path='/ready')

    assert result.status_code == 418
    assert result.text == 'ready'
    assert result.headers['x-ready'] == 'yes'
    assert 'x-discarded' not in result.headers


@pytest.mark.asyncio
async def test_controller_paths_kwargs_and_mount() -> None:
    @controller('/base', status_code=201, response_exclude_none=True)
    class Endpoints:
        @get('/override', status_code=202)
        async def override(self) -> dict[str, int | None]:
            return {'value': 1, 'omitted': None}

        @post()
        async def inherited(self) -> dict[str, int | None]:
            return {'value': 2, 'omitted': None}

    app = Rapidy(http_route_handlers=[Endpoints])
    async with app.lifespan.ctx_manager():
        override = await request(app, path='/base/override')
        inherited = await request(app, method='POST', path='/base')

    assert override.status_code == 202
    assert override.json() == {'value': 1}
    assert inherited.status_code == 201
    assert inherited.json() == {'value': 2}

    @controller('/nested')
    class NestedEndpoints:
        @get('/x')
        async def x(self) -> str:
            return 'nested'

    mounted = Rapidy(http_route_handlers=[HTTPRouter('/v1', route_handlers=[NestedEndpoints])])
    async with mounted.lifespan.ctx_manager():
        nested = await request(mounted, path='/v1/nested/x')
    assert nested.text == 'nested'


@pytest.mark.asyncio
async def test_view_controller_dispatch_and_registration_lifecycle() -> None:
    init_calls = 0

    class EndpointsView(View):
        def __init__(self, request: Request) -> None:
            nonlocal init_calls
            init_calls += 1
            super().__init__(request)

        async def get(self) -> str:
            return 'get'

        async def post(self) -> str:
            return 'post'

    view_route = controller('/view')(EndpointsView)
    app = Rapidy(http_route_handlers=[view_route])
    assert init_calls == 0
    async with app.lifespan.ctx_manager():
        assert (await request(app, path='/view')).text == 'get'
        assert (await request(app, method='POST', path='/view')).text == 'post'
        assert (await request(app, method='DELETE', path='/view')).status_code == 405
    assert init_calls == 2

    with pytest.raises(HandlerIsNotAsyncFuncTypeError):
        get.reg('/invalid-view', EndpointsView)

    class RegisteredView(View):
        async def get(self) -> str:
            return 'registered'

    registered_app = Rapidy(http_route_handlers=[controller.reg('/registered-view', RegisteredView)])
    async with registered_app.lifespan.ctx_manager():
        assert (await request(registered_app, path='/registered-view')).text == 'registered'
