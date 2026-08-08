from http import HTTPStatus
from typing import Any, Callable, Coroutine
from typing_extensions import Annotated, Final

import pytest
from rapidy_core.enums import ContentType
from rapidy_core.parameters.http import Body, Header

from rapidy import Rapidy
from rapidy.http import middleware, normalize_path_middleware, post, Request, Response, StreamResponse
from rapidy.typedefs import CallNext, Middleware
from tests.ported.client import AppClientFactory

BEARER_TOKEN: Final[str] = 'Bearer <SomeToken>'
REQUEST_ID: Final[str] = '<SomeRequestID>'
BODY_DATA: Final[str] = '<SomeBodyTextData>'


@middleware
async def new_style_auth_middleware(
    request: Request,
    call_next: CallNext,
    bearer_token: Annotated[str, Header(alias='Authorization')],
) -> StreamResponse:
    assert bearer_token == BEARER_TOKEN
    return await call_next(request)


async def raw_auth_middleware(request: Request, call_next: CallNext) -> Response:
    assert request.headers.get('Authorization') == BEARER_TOKEN
    return await call_next(request)


@middleware
async def new_style_request_id_middleware(
    request: Request,
    handler: CallNext,
    request_id: Annotated[str, Header(alias='Request-ID')],
) -> StreamResponse:
    assert request_id == REQUEST_ID
    return await handler(request)


async def raw_request_id_middleware(request: Request, call_next: CallNext) -> Response:
    assert request.headers.get('Request-ID') == REQUEST_ID
    return await call_next(request)


async def unsupported_old_style_request_id_middleware(
    app: Rapidy,
    handler: CallNext,
) -> Callable[[Request, str], Coroutine[Any, Any, StreamResponse]]:
    async def middleware_handler(
        request: Request,
        request_id: Annotated[str, Header(alias='Request-ID')],
    ) -> StreamResponse:
        assert request_id == REQUEST_ID
        return await handler(request)

    return middleware_handler


async def test_success(app_client: AppClientFactory) -> None:
    @middleware
    async def simple_middleware(request: Request, call_next: CallNext) -> StreamResponse:
        return await call_next(request)

    async def handler() -> Response:
        return Response()

    app = Rapidy(middlewares=[simple_middleware], http_route_handlers=[post.reg('/', handler)])
    client = await app_client(app)
    resp = await client.post('/', data='1')
    assert resp.status == HTTPStatus.OK


async def test_success_parametrized_middleware(app_client: AppClientFactory) -> None:
    test_parameter: Final[str] = 'awesome'

    def parametrized_middleware(parameter: str) -> Middleware:
        @middleware
        async def inner_middleware(request: Request, handler: CallNext) -> StreamResponse:
            request.state.parameter = parameter
            return await handler(request)

        return inner_middleware

    async def handler(request: Request) -> Response:
        assert request.state.parameter == test_parameter
        return Response()

    app = Rapidy(
        middlewares=[parametrized_middleware(parameter=test_parameter)],
        http_route_handlers=[post.reg('/', handler)],
    )
    client = await app_client(app)
    resp = await client.post('/', data='1')
    assert resp.status == HTTPStatus.OK


@pytest.mark.parametrize(
    'auth_middleware, request_id_middleware',
    [
        pytest.param(new_style_auth_middleware, new_style_request_id_middleware, id='new-style-middlewares'),
        pytest.param(raw_auth_middleware, raw_request_id_middleware, id='raw-middlewares'),
    ],
)
async def test_multiple_new_style_middlewares_validation(
    app_client: AppClientFactory,
    auth_middleware: Middleware,
    request_id_middleware: Middleware,
) -> None:
    async def handler(body: Annotated[str, Body(content_type=ContentType.text_plain)]) -> Response:
        assert body == BODY_DATA
        return Response()

    app = Rapidy(
        middlewares=[normalize_path_middleware(), auth_middleware, request_id_middleware],
        http_route_handlers=[post.reg('/', handler)],
    )
    client = await app_client(app)
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
        pytest.param(raw_auth_middleware, raw_request_id_middleware, id='raw-middlewares'),
    ],
)
async def test_multiple_new_style_middlewares_in_subapp_validation(
    app_client: AppClientFactory,
    auth_middleware: Middleware,
    request_id_middleware: Middleware,
) -> None:
    async def protected_handler(body: Annotated[str, Body(content_type=ContentType.text_plain)]) -> Response:
        assert body == BODY_DATA
        return Response()

    api_app = Rapidy(
        middlewares=[auth_middleware],
        http_route_handlers=[post.reg('/protected_handler', protected_handler)],
    )

    app = Rapidy(middlewares=[normalize_path_middleware(), request_id_middleware])
    app.add_subapp('/security', api_app)

    client = await app_client(app)
    resp = await client.post(
        '/security/protected_handler',
        headers={
            'Authorization': BEARER_TOKEN,
            'Request-ID': REQUEST_ID,
        },
        data=BODY_DATA,
    )
    assert resp.status == HTTPStatus.OK


async def test_unsupported_old_style_middleware(app_client: AppClientFactory) -> None:
    async def handler(body: Annotated[str, Body()]) -> Response:
        assert body == BODY_DATA
        return Response()

    app = Rapidy(
        middlewares=[unsupported_old_style_request_id_middleware],
        http_route_handlers=[post.reg('/', handler)],
    )

    client = await app_client(app)
    resp = await client.post(
        '/',
        headers={'Request-ID': REQUEST_ID},
        data=BODY_DATA,
    )
    assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR


async def test_rename_snd_attr(app_client: AppClientFactory) -> None:
    @middleware
    async def simple_middleware(request: Request, call_next: CallNext) -> StreamResponse:
        return await call_next(request)

    async def handler() -> Any:
        pass

    app = Rapidy(middlewares=[simple_middleware], http_route_handlers=[post.reg('/', handler)])
    client = await app_client(app)
    resp = await client.post('/')
    assert resp.status == HTTPStatus.OK
