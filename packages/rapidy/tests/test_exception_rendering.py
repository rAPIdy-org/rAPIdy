from __future__ import annotations

import logging
from collections import deque
from typing import Any

import httpx
import pytest
from pydantic import BaseModel

from rapidy import Rapidy
from rapidy.exceptions import (
    HTTPFound,
    HTTPMethodNotAllowed,
    HTTPNotFound,
    HTTPOk,
    HTTPValidationFailure,
)
from rapidy.http import Body, get, post, Request, Response
from rapidy.routing.http.routers import HTTPRouter
from rapidy.typedefs import CallNext, Middleware


async def request(app: Rapidy, method: str = 'GET', path: str = '/', **kwargs: Any) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url='http://testserver',
    ) as client:
        return await client.request(method, path, **kwargs)


async def asgi_request(
    app: Rapidy,
    *,
    method: str = 'GET',
    path: str = '/',
    body: bytes = b'',
    receive_messages: list[dict[str, Any]] | None = None,
    expected_exception: type[Exception] | None = None,
) -> list[dict[str, Any]]:
    incoming = deque(
        receive_messages
        or [{'type': 'http.request', 'body': body, 'more_body': False}]
    )
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        if incoming:
            return incoming.popleft()
        return {'type': 'http.disconnect'}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    scope = {
        'type': 'http',
        'asgi': {'version': '3.0'},
        'http_version': '1.1',
        'method': method,
        'scheme': 'http',
        'path': path,
        'raw_path': path.encode(),
        'query_string': b'',
        'headers': [(b'content-length', str(len(body)).encode())],
        'client': ('127.0.0.1', 1234),
        'server': ('testserver', 80),
    }
    async with app.lifespan.ctx_manager():
        if expected_exception is None:
            await app(scope, receive, send)
        else:
            with pytest.raises(expected_exception):
                await app(scope, receive, send)
    return sent


@pytest.mark.asyncio
async def test_render_404_from_handler() -> None:
    @get('/')
    async def handler() -> None:
        raise HTTPNotFound

    app = Rapidy(http_route_handlers=[handler])
    async with app.lifespan.ctx_manager():
        response = await request(app)

    assert response.status_code == 404
    assert response.text == '404: Not Found'
    assert response.headers['content-type'].startswith('text/plain')


@pytest.mark.asyncio
async def test_render_302_location() -> None:
    @get('/')
    async def handler() -> None:
        raise HTTPFound('/next')

    app = Rapidy(http_route_handlers=[handler])
    async with app.lifespan.ctx_manager():
        response = await request(app)

    assert response.status_code == 302
    assert response.headers['location'] == '/next'


@pytest.mark.asyncio
async def test_render_405_allow() -> None:
    @get('/')
    async def handler() -> None:
        raise HTTPMethodNotAllowed('POST', ['GET'])

    app = Rapidy(http_route_handlers=[handler])
    async with app.lifespan.ctx_manager():
        response = await request(app)

    assert response.status_code == 405
    assert response.headers['allow'] == 'GET'


@pytest.mark.asyncio
async def test_render_422_schema() -> None:
    @get('/')
    async def handler() -> None:
        raise HTTPValidationFailure(
            [{'loc': ('body', 'field'), 'msg': 'field required', 'type': 'missing'}],
        )

    app = Rapidy(http_route_handlers=[handler])
    async with app.lifespan.ctx_manager():
        response = await request(app)

    assert response.status_code == 422
    assert response.headers['content-type'].startswith('application/json')
    assert response.json()['errors'][0] == {
        'loc': ['body', 'field'],
        'msg': 'field required',
        'type': 'missing',
    }


@pytest.mark.asyncio
async def test_matcher_404_405_regress() -> None:
    @get('/exists')
    async def handler() -> str:
        return 'ok'

    app = Rapidy(http_route_handlers=[handler])
    async with app.lifespan.ctx_manager():
        missing = await request(app, path='/missing')
        wrong_method = await request(app, method='POST', path='/exists')

    assert missing.status_code == 404
    assert wrong_method.status_code == 405
    assert wrong_method.headers['allow'] == 'GET, HEAD'


class Payload(BaseModel):
    name: str


@pytest.mark.asyncio
async def test_body_validation_422_regress() -> None:
    @post('/items')
    async def create(payload: Payload = Body()) -> str:
        return payload.name

    app = Rapidy(http_route_handlers=[create])
    async with app.lifespan.ctx_manager():
        response = await request(app, method='POST', path='/items', json={})

    assert response.status_code == 422
    assert response.json()['errors'][0]['loc'][0] == 'body'


@pytest.mark.asyncio
async def test_client_max_size_413_regress() -> None:
    @post('/body')
    async def read_body(current_request: Request) -> str:
        return str(len(await current_request.read()))

    app = Rapidy(client_max_size=16, http_route_handlers=[read_body])
    payload = b'x' * 32
    async with app.lifespan.ctx_manager():
        response = await request(app, method='POST', path='/body', content=payload)

    assert response.status_code == 413
    assert '16' in response.text
    assert '32' in response.text


def catching_middleware(exception_type: type[Exception], marker: list[str]) -> Middleware:
    async def current_middleware(current_request: Request, call_next: CallNext) -> Response:
        try:
            return await call_next(current_request)
        except exception_type:
            marker.append('caught')
            return Response('recovered')

    return current_middleware


async def assert_middleware_catches_exception(
    exception: Exception,
    caplog: pytest.LogCaptureFixture,
) -> None:
    marker: list[str] = []

    @get('/')
    async def handler() -> None:
        raise exception

    caplog.set_level(logging.ERROR, logger='rapidy.application')
    app = Rapidy(
        middlewares=[catching_middleware(type(exception), marker)],
        http_route_handlers=[handler],
    )
    async with app.lifespan.ctx_manager():
        response = await request(app)

    assert response.text == 'recovered'
    assert marker == ['caught']
    assert not caplog.records


@pytest.mark.asyncio
async def test_middleware_catches_http_exception(caplog: pytest.LogCaptureFixture) -> None:
    await assert_middleware_catches_exception(HTTPNotFound(), caplog)


@pytest.mark.asyncio
async def test_middleware_catches_value_error(caplog: pytest.LogCaptureFixture) -> None:
    await assert_middleware_catches_exception(ValueError('boom'), caplog)


@pytest.mark.asyncio
async def test_uncaught_http_exception_rendered_by_core() -> None:
    async def passthrough(current_request: Request, call_next: CallNext) -> Response:
        return await call_next(current_request)

    @get('/')
    async def handler() -> None:
        raise HTTPNotFound

    app = Rapidy(middlewares=[passthrough], http_route_handlers=[handler])
    async with app.lifespan.ctx_manager():
        response = await request(app)

    assert response.status_code == 404
    assert response.text == '404: Not Found'


@pytest.mark.asyncio
async def test_subapp_exception_through_both_onions() -> None:
    markers: list[str] = []

    def marker_middleware(name: str) -> Middleware:
        async def current_middleware(current_request: Request, call_next: CallNext) -> Response:
            markers.append(name)
            return await call_next(current_request)

        return current_middleware

    @get('/')
    async def handler() -> None:
        raise HTTPNotFound

    router = HTTPRouter('/v1', [handler], middlewares=[marker_middleware('subapp')])
    app = Rapidy(middlewares=[marker_middleware('root')], http_route_handlers=[router])
    messages = await asgi_request(app, path='/v1/')

    starts = [message for message in messages if message['type'] == 'http.response.start']
    assert len(starts) == 1
    assert starts[0]['status'] == 404
    assert markers == ['root', 'subapp']


@pytest.mark.asyncio
async def test_http_successful_early_exit(caplog: pytest.LogCaptureFixture) -> None:
    @get('/')
    async def handler() -> None:
        raise HTTPOk

    caplog.set_level(logging.ERROR, logger='rapidy.application')
    app = Rapidy(http_route_handlers=[handler])
    async with app.lifespan.ctx_manager():
        response = await request(app)

    assert response.status_code == 200
    assert response.text == '200: OK'
    assert not caplog.records


@pytest.mark.asyncio
async def test_unhandled_exception_500(caplog: pytest.LogCaptureFixture) -> None:
    @get('/')
    async def handler() -> None:
        raise ValueError('boom')

    caplog.set_level(logging.ERROR, logger='rapidy.application')
    app = Rapidy(http_route_handlers=[handler])
    async with app.lifespan.ctx_manager():
        response = await request(app)

    assert response.status_code == 500
    assert response.text == '500: Internal Server Error'
    assert response.headers['content-type'].startswith('text/plain')
    assert any(
        record.exc_info is not None and isinstance(record.exc_info[1], ValueError)
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_no_second_response_start_after_started(caplog: pytest.LogCaptureFixture) -> None:
    @get('/')
    async def handler(current_request: Request) -> None:
        await current_request._asgi_send(
            {'type': 'http.response.start', 'status': 200, 'headers': []},
        )
        raise ValueError

    caplog.set_level(logging.ERROR, logger='rapidy.application')
    messages = await asgi_request(
        Rapidy(http_route_handlers=[handler]),
        expected_exception=ValueError,
    )

    assert sum(message['type'] == 'http.response.start' for message in messages) == 1
    assert not any(message['type'] == 'http.response.body' for message in messages)
    assert any(record.exc_info is not None for record in caplog.records)


@pytest.mark.asyncio
async def test_client_disconnect_while_reading_body(caplog: pytest.LogCaptureFixture) -> None:
    @post('/')
    async def handler(current_request: Request) -> str:
        await current_request.read()
        return 'unreachable'

    caplog.set_level(logging.DEBUG, logger='rapidy.application')
    messages = await asgi_request(
        Rapidy(http_route_handlers=[handler]),
        method='POST',
        body=b'part',
        receive_messages=[
            {'type': 'http.request', 'body': b'part', 'more_body': True},
            {'type': 'http.disconnect'},
        ],
    )

    assert not any(message['type'] == 'http.response.start' for message in messages)
    assert not any(record.levelno >= logging.ERROR for record in caplog.records)


@pytest.mark.asyncio
async def test_handler_connection_reset_is_not_misclassified_as_client_disconnect(
    caplog: pytest.LogCaptureFixture,
) -> None:
    @get('/')
    async def handler() -> None:
        msg = 'database connection was reset'
        raise ConnectionResetError(msg)

    caplog.set_level(logging.ERROR, logger='rapidy.application')
    app = Rapidy(http_route_handlers=[handler])
    async with app.lifespan.ctx_manager():
        response = await request(app)

    assert response.status_code == 500
    assert any(
        record.exc_info is not None and isinstance(record.exc_info[1], ConnectionResetError)
        for record in caplog.records
    )
