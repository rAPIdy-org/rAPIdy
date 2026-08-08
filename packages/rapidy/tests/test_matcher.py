from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from rapidy import Rapidy
from rapidy.exceptions import HTTPMethodNotAllowed, HTTPNotFound
from rapidy.request import Request
from rapidy.response import Response
from rapidy.routing.http.base import IncorrectPathError, RouterTypeError
from rapidy.routing.http.routers import (
    delete,
    get,
    HandlerIsNotAsyncFuncTypeError,
    head,
    MissingPathError,
    options,
    patch,
    post,
    put,
)
from rapidy.routing.matcher import DuplicateRouteError, PathTemplateError, UrlMatcher


async def first_terminal(_: Request) -> Response:
    return Response('first')


async def second_terminal(_: Request) -> Response:
    return Response('second')


def add_route(
    matcher: UrlMatcher,
    method: str,
    path: str,
    terminal: Callable[[Request], Any] = first_terminal,
    *,
    allow_head: bool = True,
) -> None:
    matcher.add_route(method, path, terminal, {}, allow_head=allow_head)


class TestUrlMatcherUnit:
    def test_named_parameter(self) -> None:
        matcher = UrlMatcher()
        add_route(matcher, 'GET', '/users/{user_id}')

        match = matcher.resolve('GET', '/users/42')

        assert match.path_params == {'user_id': '42'}

    def test_custom_regex_and_quantifier_braces(self) -> None:
        matcher = UrlMatcher()
        add_route(matcher, 'GET', r'/api/{version:\d+}/x')
        add_route(matcher, 'GET', r'/digits/{value:\d{2}}')

        assert matcher.resolve('GET', '/api/1/x').path_params == {'version': '1'}
        assert matcher.resolve('GET', '/digits/12').path_params == {'value': '12'}
        with pytest.raises(HTTPNotFound):
            matcher.resolve('GET', '/api/v1/x')

    def test_tail_parameter_captures_slashes(self) -> None:
        matcher = UrlMatcher()
        add_route(matcher, 'GET', r'/files/{version:\d+}/{tail:.*}')

        match = matcher.resolve('GET', '/files/1/a/b/c.txt')

        assert match.path_params == {'version': '1', 'tail': 'a/b/c.txt'}

    def test_static_route_wins_over_earlier_dynamic_route(self) -> None:
        matcher = UrlMatcher()
        add_route(matcher, 'GET', '/users/{user_id}', first_terminal)
        add_route(matcher, 'GET', '/users/me', second_terminal)

        assert matcher.resolve('GET', '/users/me').terminal is second_terminal

    def test_dynamic_routes_preserve_registration_order(self) -> None:
        matcher = UrlMatcher()
        add_route(matcher, 'GET', '/items/{value}', first_terminal)
        add_route(matcher, 'GET', '/items/{value:.*}', second_terminal)

        assert matcher.resolve('GET', '/items/one').terminal is first_terminal

    def test_unknown_path_raises_not_found(self) -> None:
        with pytest.raises(HTTPNotFound):
            UrlMatcher().resolve('GET', '/missing')

    def test_method_not_allowed_includes_auto_head(self) -> None:
        matcher = UrlMatcher()
        add_route(matcher, 'GET', '/ping')

        with pytest.raises(HTTPMethodNotAllowed) as exc_info:
            matcher.resolve('POST', '/ping')

        assert exc_info.value.allowed_methods == {'GET', 'HEAD'}
        assert exc_info.value.headers['Allow'] == 'GET, HEAD'

    def test_allow_head_false_keeps_get_in_allow_header(self) -> None:
        matcher = UrlMatcher()
        add_route(matcher, 'GET', '/x', allow_head=False)

        with pytest.raises(HTTPMethodNotAllowed) as exc_info:
            matcher.resolve('HEAD', '/x')

        assert exc_info.value.allowed_methods == {'GET'}
        assert exc_info.value.headers['Allow'] == 'GET'

    @pytest.mark.parametrize('explicit_first', [False, True])
    def test_explicit_head_wins_over_auto_head(self, explicit_first: bool) -> None:
        matcher = UrlMatcher()
        registrations = (
            [('HEAD', second_terminal), ('GET', first_terminal)]
            if explicit_first
            else [('GET', first_terminal), ('HEAD', second_terminal)]
        )
        for method, terminal in registrations:
            add_route(matcher, method, '/head', terminal)

        assert matcher.resolve('HEAD', '/head').terminal is second_terminal
        head_records = [record for record in matcher.routes if record.method == 'HEAD']
        assert len(head_records) == 1
        assert head_records[0].is_auto_head is False

    def test_duplicate_route_fails_during_registration(self) -> None:
        matcher = UrlMatcher()
        add_route(matcher, 'GET', '/duplicate')

        with pytest.raises(DuplicateRouteError):
            add_route(matcher, 'GET', '/duplicate')

    @pytest.mark.parametrize('path', ['/x/{not-valid}', '/x/{value}/{value}', '/x/{open'])
    def test_invalid_path_template_fails_during_registration(self, path: str) -> None:
        with pytest.raises(PathTemplateError):
            add_route(UrlMatcher(), 'GET', path)

    def test_mount_prefixes_are_sorted_longest_first(self) -> None:
        matcher = UrlMatcher()
        matcher.add_prefix('/api', object())
        matcher.add_prefix('/api/internal', object())
        matcher.add_prefix('/x', object())

        # This is the single white-box test allowed for the milestone-08 mount placeholder.
        assert [prefix for prefix, _ in matcher._prefixes] == ['/api/internal', '/api', '/x']

    def test_routes_snapshot_marks_auto_head(self) -> None:
        matcher = UrlMatcher()
        add_route(matcher, 'GET', '/a')
        add_route(matcher, 'POST', '/b')

        assert [(record.path, record.method, record.is_auto_head) for record in matcher.routes] == [
            ('/a', 'GET', False),
            ('/a', 'HEAD', True),
            ('/b', 'POST', False),
        ]


@get('/ping')
async def ping() -> str:
    return 'pong'


@get('/no-head', allow_head=False)
async def no_head() -> str:
    return 'get-only'


@get('/explicit-head')
async def explicit_head_get() -> str:
    return 'auto'


@head('/explicit-head')
async def explicit_head_handler() -> str:
    return 'explicit'


@options('/options')
async def options_handler() -> str:
    return 'options'


@get('/users/{user_id}')
async def dynamic_user(request: Request) -> str:
    return f'dynamic:{request.path_params["user_id"]}'


@get('/users/me')
async def static_user() -> str:
    return 'static:me'


@get(r'/files/{version:\d+}/{tail:.*}')
async def file_path(request: Request) -> str:
    return f'{request.path_params["version"]}:{request.path_params["tail"]}'


def matcher_app() -> Rapidy:
    return Rapidy(
        http_route_handlers=[
            ping,
            no_head,
            explicit_head_get,
            explicit_head_handler,
            options_handler,
            dynamic_user,
            static_user,
            file_path,
        ]
    )


@pytest.mark.asyncio
async def test_e2e_head_allow_and_not_found() -> None:
    async with AsyncClient(transport=ASGITransport(app=matcher_app()), base_url='http://test') as client:
        get_response = await client.get('/ping')
        head_response = await client.head('/ping')
        no_head_response = await client.head('/no-head')
        method_response = await client.post('/ping')
        missing_response = await client.get('/missing')

    assert get_response.status_code == 200
    assert get_response.text == 'pong'
    assert head_response.status_code == 200
    assert head_response.content == b''
    assert head_response.headers['content-length'] == '4'
    assert no_head_response.status_code == 405
    assert no_head_response.headers['allow'] == 'GET'
    assert method_response.status_code == 405
    assert method_response.headers['allow'] == 'GET, HEAD'
    assert missing_response.status_code == 404


@pytest.mark.asyncio
async def test_e2e_explicit_head_and_options() -> None:
    async with AsyncClient(transport=ASGITransport(app=matcher_app()), base_url='http://test') as client:
        head_response = await client.head('/explicit-head')
        options_response = await client.options('/options')
        missing_options = await client.options('/ping')

    assert head_response.status_code == 200
    assert head_response.content == b''
    assert head_response.headers['content-length'] == str(len('explicit'))
    assert options_response.status_code == 200
    assert options_response.text == 'options'
    assert missing_options.status_code == 405
    assert 'OPTIONS' not in missing_options.headers['allow']


@pytest.mark.asyncio
async def test_e2e_static_priority_regex_and_tail() -> None:
    async with AsyncClient(transport=ASGITransport(app=matcher_app()), base_url='http://test') as client:
        static_response = await client.get('/users/me')
        dynamic_response = await client.get('/users/42')
        tail_response = await client.get('/files/12/a/b.txt')

    assert static_response.text == 'static:me'
    assert dynamic_response.text == 'dynamic:42'
    assert tail_response.text == '12:a/b.txt'


@pytest.mark.parametrize(
    ('decorator', 'method'),
    [
        (get, 'GET'),
        (post, 'POST'),
        (put, 'PUT'),
        (patch, 'PATCH'),
        (delete, 'DELETE'),
        (head, 'HEAD'),
        (options, 'OPTIONS'),
    ],
)
@pytest.mark.asyncio
async def test_all_method_decorators_register(decorator: Any, method: str) -> None:
    async def handler() -> str:
        return method

    route = decorator('/method')(handler)
    app = Rapidy(http_route_handlers=[route])
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.request(method, '/method')

    assert response.status_code == 200
    if method == 'HEAD':
        assert response.content == b''
    else:
        assert response.text == method


def test_router_registration_errors() -> None:
    with pytest.raises(IncorrectPathError):
        get('bad-path')

    def sync_handler() -> None:
        return None

    with pytest.raises(HandlerIsNotAsyncFuncTypeError):
        get('/sync')(sync_handler)

    async def missing_path_handler() -> None:
        return None

    missing_path = get()(missing_path_handler)
    with pytest.raises(MissingPathError):
        Rapidy().add_http_router(missing_path)
    with pytest.raises(RouterTypeError):
        Rapidy().add_http_router(object())


@pytest.mark.asyncio
async def test_root_path_is_stripped_before_match() -> None:
    messages: list[dict[str, Any]] = []
    scope: dict[str, Any] = {
        'type': 'http',
        'method': 'GET',
        'path': '/api/ping',
        'root_path': '/api',
        'headers': [],
    }

    async def receive() -> dict[str, Any]:
        return {'type': 'http.request', 'body': b'', 'more_body': False}

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    await Rapidy(http_route_handlers=[ping])(scope, receive, send)

    assert messages[0]['status'] == 200
    assert messages[1]['body'] == b'pong'
