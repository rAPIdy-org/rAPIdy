from __future__ import annotations

from typing import Any

import httpx
import pytest
from pydantic import BaseModel
from rapidy_core.enums import ContentType

import rapidy.application as application_module
from rapidy import Rapidy
from rapidy.exceptions import HTTPNotFound
from rapidy.http import get, Header, Request, Response
from rapidy.middlewares import middleware, normalize_path_middleware
from rapidy.middlewares.runner import MiddlewareIsNotAsyncFuncTypeError
from rapidy.typedefs import CallNext


async def get_response(app: Rapidy, path: str = '/', **kwargs: Any) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url='http://testserver',
    ) as client:
        return await client.get(path, **kwargs)


@pytest.mark.asyncio
async def test_onion_order() -> None:
    events: list[str] = []

    async def first(request: Request, call_next: CallNext) -> Response:
        events.append('m1_before')
        response = await call_next(request)
        events.append('m1_after')
        return response

    async def second(request: Request, call_next: CallNext) -> Response:
        events.append('m2_before')
        response = await call_next(request)
        events.append('m2_after')
        return response

    @get('/')
    async def handler() -> str:
        events.append('handler')
        return 'ok'

    app = Rapidy(middlewares=[first, second], http_route_handlers=[handler])
    async with app.lifespan.ctx_manager():
        response = await get_response(app)

    assert response.text == 'ok'
    assert events == ['m1_before', 'm2_before', 'handler', 'm2_after', 'm1_after']


@pytest.mark.asyncio
async def test_short_circuit() -> None:
    events: list[str] = []

    async def outer(_request: Request, call_next: CallNext) -> Response:
        del call_next
        events.append('outer')
        return Response('short')

    async def inner(request: Request, call_next: CallNext) -> Response:
        events.append('inner')
        return await call_next(request)

    @get('/')
    async def handler() -> str:
        events.append('handler')
        return 'handler'

    app = Rapidy(middlewares=[outer, inner], http_route_handlers=[handler])
    async with app.lifespan.ctx_manager():
        response = await get_response(app)

    assert response.text == 'short'
    assert events == ['outer']


@pytest.mark.asyncio
async def test_exception_reaches_outer_middleware() -> None:
    events: list[str] = []

    async def catcher(request: Request, call_next: CallNext) -> Response:
        try:
            return await call_next(request)
        except RuntimeError:
            events.append('caught')
            return Response('recovered')

    @get('/')
    async def handler() -> None:
        raise RuntimeError('expected')

    app = Rapidy(middlewares=[catcher], http_route_handlers=[handler])
    async with app.lifespan.ctx_manager():
        response = await get_response(app)

    assert response.text == 'recovered'
    assert events == ['caught']


class MiddlewareResult(BaseModel):
    value: int
    omitted: str | None = None


async def assert_middleware_json(result: Any, expected: dict[str, int]) -> None:
    @middleware(
        status_code=201,
        response_content_type=ContentType.json,
        response_exclude_none=True,
    )
    async def short_circuit(_request: Request, _call_next: CallNext) -> Any:
        return result

    app = Rapidy(middlewares=[short_circuit])
    async with app.lifespan.ctx_manager():
        response = await get_response(app)

    assert response.status_code == 201
    assert response.headers['content-type'] == 'application/json; charset=utf-8'
    assert response.json() == expected


@pytest.mark.asyncio
async def test_middleware_returns_dict() -> None:
    await assert_middleware_json({'value': 1, 'omitted': None}, {'value': 1})


@pytest.mark.asyncio
async def test_middleware_returns_pydantic() -> None:
    await assert_middleware_json(MiddlewareResult(value=2), {'value': 2})


@pytest.mark.asyncio
async def test_middleware_param_extraction() -> None:
    seen: list[str] = []

    @middleware
    async def token_middleware(
        request: Request,
        call_next: CallNext,
        token: str = Header(alias='X-Token'),
    ) -> Response:
        seen.append(token)
        return await call_next(request)

    @get('/')
    async def handler() -> str:
        return 'ok'

    app = Rapidy(middlewares=[token_middleware], http_route_handlers=[handler])
    async with app.lifespan.ctx_manager():
        response = await get_response(app, headers={'x-token': 'secret'})

    assert response.text == 'ok'
    assert seen == ['secret']


@pytest.mark.asyncio
async def test_plain_middleware_runs_as_is() -> None:
    seen: list[str] = []

    async def plain(request: Request, call_next: CallNext) -> Response:
        seen.append('plain')
        return await call_next(request)

    @get('/')
    async def handler() -> str:
        return 'ok'

    app = Rapidy(middlewares=[plain], http_route_handlers=[handler])
    async with app.lifespan.ctx_manager():
        assert (await get_response(app)).text == 'ok'
    assert seen == ['plain']


@pytest.mark.asyncio
async def test_sync_middleware_fails_at_startup() -> None:
    def invalid(_request: Request, _call_next: CallNext) -> Response:
        return Response()

    invalid_app = Rapidy(middlewares=[invalid])
    with pytest.raises(MiddlewareIsNotAsyncFuncTypeError):
        async with invalid_app.lifespan.ctx_manager():
            pass


@pytest.mark.asyncio
async def test_onion_built_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0
    original = application_module.build_onion

    def counted_build(*args: Any, **kwargs: Any) -> CallNext:
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(application_module, 'build_onion', counted_build)

    @get('/')
    async def handler() -> str:
        return 'ok'

    app = Rapidy(http_route_handlers=[handler])
    async with app.lifespan.ctx_manager():
        startup_calls = calls
        assert startup_calls >= 1
        await get_response(app)
        await get_response(app)
        assert calls == startup_calls


@pytest.mark.asyncio
async def test_middleware_sees_unmatched_404() -> None:
    async def catch_not_found(request: Request, call_next: CallNext) -> Response:
        try:
            return await call_next(request)
        except HTTPNotFound:
            return Response('caught')

    app = Rapidy(middlewares=[catch_not_found])
    async with app.lifespan.ctx_manager():
        response = await get_response(app, '/missing')

    assert response.status_code == 200
    assert response.text == 'caught'


@pytest.mark.asyncio
async def test_normalize_path_merge_slashes() -> None:
    @get('/a/b')
    async def handler() -> str:
        return 'ok'

    app = Rapidy(middlewares=[normalize_path_middleware()], http_route_handlers=[handler])
    async with app.lifespan.ctx_manager():
        response = await get_response(app, '/a//b?value=1')

    assert response.status_code == 308
    assert response.headers['location'] == '/a/b?value=1'


@pytest.mark.asyncio
async def test_normalize_path_append_slash() -> None:
    @get('/path/')
    async def with_slash() -> str:
        return 'slash'

    @get('/other')
    async def without_slash() -> str:
        return 'other'

    app = Rapidy(
        middlewares=[normalize_path_middleware()],
        http_route_handlers=[with_slash, without_slash],
    )
    async with app.lifespan.ctx_manager():
        appended = await get_response(app, '/path')
        unchanged = await get_response(app, '/other/')

    assert appended.status_code == 308
    assert appended.headers['location'] == '/path/'
    assert unchanged.status_code == 404

    with pytest.raises(ValueError, match='Cannot both remove and append slash'):
        normalize_path_middleware(append_slash=True, remove_slash=True)
