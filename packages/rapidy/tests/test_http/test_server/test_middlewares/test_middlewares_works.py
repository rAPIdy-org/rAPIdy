from http import HTTPStatus
from typing import Any, Awaitable, Callable, Coroutine
from typing_extensions import Annotated, Final

import pytest
from aiohttp.web_middlewares import normalize_path_middleware
from aiohttp.web_request import Request
from aiohttp.web_response import StreamResponse
from pytest_aiohttp.plugin import AiohttpClient

from rapidy import web
from rapidy.enums import ContentType
from rapidy.parameters.http import Body, Header
from rapidy.typedefs import CallNext, Middleware
from rapidy.web import middleware

BEARER_TOKEN: Final[str] = 'Bearer <SomeToken>'
REQUEST_ID: Final[str] = '<SomeRequestID>'
BODY_DATA: Final[str] = '<SomeBodyTextData>'


@middleware
async def new_style_auth_middleware(
    request: web.Request,
    call_next: CallNext,
    bearer_token: Annotated[str, Header(alias='Authorization')],
) -> web.StreamResponse:
    assert bearer_token == BEARER_TOKEN
    return await call_next(request)


async def old_style_auth_middleware(app: web.Application, handler: CallNext) -> Any:
    async def middleware_handler(request: web.Request) -> web.StreamResponse:
        assert request.headers.get('Authorization') == BEARER_TOKEN
        return await handler(request)

    return middleware_handler


@middleware
async def new_style_request_id_middleware(
    request: web.Request,
    handler: CallNext,
    request_id: Annotated[str, Header(alias='Request-ID')],
) -> web.StreamResponse:
    assert request_id == REQUEST_ID
    return await handler(request)


async def old_style_request_id_middleware(
    app: web.Application,
    call_next: CallNext,
) -> Callable[[web.Request], Awaitable[web.StreamResponse]]:
    async def middleware_handler(request: web.Request) -> web.StreamResponse:
        assert request.headers.get('Request-ID') == REQUEST_ID
        return await call_next(request)

    return middleware_handler


async def unsupported_old_style_request_id_middleware(
    app: web.Application,
    handler: CallNext,
) -> Callable[[Request, str], Coroutine[Any, Any, StreamResponse]]:
    async def middleware_handler(
        request: web.Request,
        request_id: Annotated[str, Header(alias='Request-ID')],
    ) -> web.StreamResponse:
        assert request_id == REQUEST_ID
        return await handler(request)

    return middleware_handler


async def test_success(aiohttp_client: AiohttpClient) -> None:
    @middleware
    async def simple_middleware(request: web.Request, call_next: CallNext) -> web.StreamResponse:
        return await call_next(request)

    async def handler() -> web.Response:
        return web.Response()

    app = web.Application(middlewares=[simple_middleware])
    app.add_routes([web.post('/', handler)])
    client = await aiohttp_client(app)
    resp = await client.post('/', data='1')
    assert resp.status == HTTPStatus.OK


async def test_success_parametrized_middleware(aiohttp_client: AiohttpClient) -> None:
    test_parameter: Final[str] = 'awesome'

    def parametrized_middleware(parameter: str) -> Middleware:
        @middleware
        async def inner_middleware(request: web.Request, handler: CallNext) -> web.StreamResponse:
            request['parameter'] = parameter
            return await handler(request)

        return inner_middleware

    async def handler(request: web.Request) -> web.Response:
        assert request['parameter'] == test_parameter
        return web.Response()

    app = web.Application(middlewares=[parametrized_middleware(parameter=test_parameter)])
    app.add_routes([web.post('/', handler)])
    client = await aiohttp_client(app)
    resp = await client.post('/', data='1')
    assert resp.status == HTTPStatus.OK


@pytest.mark.parametrize(
    'auth_middleware, request_id_middleware',
    [
        pytest.param(new_style_auth_middleware, new_style_request_id_middleware, id='new-style-middlewares'),
        pytest.param(old_style_auth_middleware, old_style_request_id_middleware, id='old-style-middlewares'),
    ],
)
async def test_multiple_new_style_middlewares_validation(
    aiohttp_client: AiohttpClient,
    auth_middleware: Middleware,
    request_id_middleware: Middleware,
) -> None:
    async def handler(body: Annotated[str, Body(content_type=ContentType.text_plain)]) -> web.Response:
        assert body == BODY_DATA
        return web.Response()

    app = web.Application(middlewares=[normalize_path_middleware(), auth_middleware, request_id_middleware])
    app.add_routes([web.post('/', handler)])
    client = await aiohttp_client(app)
    resp = await client.post(
        '/',
        headers={
            'Authorization': BEARER_TOKEN,
            'Request-ID': REQUEST_ID,
        },
        data=BODY_DATA,
    )
    assert resp.status == HTTPStatus.OK


@pytest.mark.parametrize(
    'auth_middleware, request_id_middleware',
    [
        pytest.param(new_style_auth_middleware, new_style_request_id_middleware, id='new-style-middlewares'),
        pytest.param(old_style_auth_middleware, old_style_request_id_middleware, id='old-style-middlewares'),
    ],
)
async def test_multiple_new_style_middlewares_in_subapp_validation(
    aiohttp_client: AiohttpClient,
    auth_middleware: Middleware,
    request_id_middleware: Middleware,
) -> None:
    async def protected_handler(body: Annotated[str, Body(content_type=ContentType.text_plain)]) -> web.Response:
        assert body == BODY_DATA
        return web.Response()

    api_app = web.Application(middlewares=[auth_middleware])
    api_app.add_routes([web.post('/protected_handler', protected_handler)])

    app = web.Application(middlewares=[normalize_path_middleware(), request_id_middleware])
    app.add_subapp('/security', api_app)

    client = await aiohttp_client(app)
    resp = await client.post(
        '/security/protected_handler',
        headers={
            'Authorization': BEARER_TOKEN,
            'Request-ID': REQUEST_ID,
        },
        data=BODY_DATA,
    )
    assert resp.status == HTTPStatus.OK


async def test_unsupported_old_style_middleware(aiohttp_client: AiohttpClient) -> None:
    async def handler(body: Annotated[str, Body()]) -> web.Response:
        assert body == BODY_DATA
        return web.Response()

    app = web.Application(middlewares=[unsupported_old_style_request_id_middleware])
    app.add_routes([web.post('/', handler)])

    client = await aiohttp_client(app)
    resp = await client.post(
        '/',
        headers={'Request-ID': REQUEST_ID},
        data=BODY_DATA,
    )
    assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR


async def test_rename_snd_attr(aiohttp_client: AiohttpClient) -> None:
    @middleware
    async def simple_middleware(request: web.Request, call_next: CallNext) -> web.StreamResponse:
        return await call_next(request)

    async def handler() -> Any:
        pass

    app = web.Application(middlewares=[simple_middleware])
    app.add_routes([web.post('/', handler)])
    client = await aiohttp_client(app)
    resp = await client.post('/')
    assert resp.status == HTTPStatus.OK
