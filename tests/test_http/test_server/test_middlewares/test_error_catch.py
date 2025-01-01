from typing import Any, Final, Optional, Union

import pytest
from aiohttp import web as aiohttp_web
from aiohttp.pytest_plugin import AiohttpClient

from rapidy import web as rapidy_web
from rapidy.typedefs import CallNext, Handler

TEXT_SUCCESS_CATCH_OK: Final[str] = 'ok'
TEXT_SUCCESS_CATCH_UNPROCESSABLE_ENTITY: Final[str] = 'unprocessable_entity'
TEXT_SUCCESS_CATCH_NOT_FOUND_ERROR: Final[str] = 'not_found_error'
TEXT_SUCCESS_CATCH_NOT_ALLOWED_ERROR: Final[str] = 'not_allowed_error'
TEXT_SUCCESS_CATCH_VALIDATION_ERROR: Final[str] = 'success_validation_error'
TEXT_NOT_CATCH: Final[str] = 'not_catch'


def errors_catch_middleware_by_web_module(web_module: Any) -> Any:
    @web_module.middleware
    async def inner(request: web_module.Request, handler: CallNext) -> web_module.StreamResponse:
        try:
            return await handler(request)
        except web_module.HTTPOk:
            return web_module.Response(body=TEXT_SUCCESS_CATCH_OK)
        except web_module.HTTPUnprocessableEntity:
            return web_module.Response(body=TEXT_SUCCESS_CATCH_UNPROCESSABLE_ENTITY)
        except Exception:
            return web_module.Response(body=TEXT_NOT_CATCH)

    return inner


@rapidy_web.middleware
async def rapidy_validation_errors_catch_middleware(
    request: rapidy_web.Request,
    call_next: CallNext,
) -> rapidy_web.StreamResponse:
    try:
        return await call_next(request)
    except rapidy_web.HTTPNotFound:
        return rapidy_web.Response(body=TEXT_SUCCESS_CATCH_NOT_FOUND_ERROR)
    except rapidy_web.HTTPMethodNotAllowed:
        return rapidy_web.Response(body=TEXT_SUCCESS_CATCH_NOT_ALLOWED_ERROR)
    except rapidy_web.HTTPValidationFailure:
        return rapidy_web.Response(body=TEXT_SUCCESS_CATCH_VALIDATION_ERROR)
    except Exception:
        return rapidy_web.Response(body=TEXT_NOT_CATCH)


@pytest.mark.parametrize(
    'middleware_web_module',
    [
        pytest.param(aiohttp_web, id='aiohttp-middleware'),
        pytest.param(rapidy_web, id='rapidy-middleware'),
    ],
)
@pytest.mark.parametrize(
    'app_web_module',
    [
        pytest.param(aiohttp_web, id='aiohttp-app'),
        pytest.param(rapidy_web, id='rapidy-app'),
    ],
)
async def test_backward_compatibility_middleware(
    aiohttp_client: AiohttpClient,
    app_web_module: Any,
    middleware_web_module: Any,
) -> None:
    @middleware_web_module.middleware
    async def middleware_manually_raise_error(
        request: rapidy_web.Request,
        handler: CallNext,
    ) -> middleware_web_module.StreamResponse:
        raise middleware_web_module.HTTPOk(text=TEXT_SUCCESS_CATCH_OK)

    app = app_web_module.Application(
        middlewares=[errors_catch_middleware_by_web_module(app_web_module), middleware_manually_raise_error],
    )
    await _test(aiohttp_client=aiohttp_client, app=app, expected_text=TEXT_SUCCESS_CATCH_OK, web_module=app_web_module)


@pytest.mark.parametrize('middleware_web_module', [aiohttp_web, rapidy_web])
async def test_success_catch_unprocessable_entity_with_rapidy_middleware_validation(
    aiohttp_client: AiohttpClient,
    middleware_web_module: Any,
) -> None:
    @rapidy_web.middleware
    async def middleware_validation_failure(
        request: rapidy_web.Request,
        handler: CallNext,
        body: str = rapidy_web.Body(),  # raises HTTPValidationFailure
    ) -> rapidy_web.StreamResponse:
        raise rapidy_web.HTTPInternalServerError(text=TEXT_NOT_CATCH)

    app = rapidy_web.Application(
        middlewares=[errors_catch_middleware_by_web_module(middleware_web_module), middleware_validation_failure],
    )
    await _test(aiohttp_client=aiohttp_client, app=app, expected_text=TEXT_SUCCESS_CATCH_UNPROCESSABLE_ENTITY)


async def test_success_catch_unprocessable_entity_with_rapidy_handler_validation(aiohttp_client: AiohttpClient) -> None:
    app = rapidy_web.Application(middlewares=[errors_catch_middleware_by_web_module(rapidy_web)])

    async def handler(
        body: str = rapidy_web.Body(),  # raises HTTPValidationFailure
    ) -> rapidy_web.Response:
        return rapidy_web.Response(body=TEXT_NOT_CATCH)

    await _test(
        aiohttp_client=aiohttp_client,
        app=app,
        handler=handler,
        expected_text=TEXT_SUCCESS_CATCH_UNPROCESSABLE_ENTITY,
    )


async def test_success_rapidy_catch_middleware_validation_failure(aiohttp_client: AiohttpClient) -> None:
    @rapidy_web.middleware
    async def middleware_validation_failure(
        request: rapidy_web.Request,
        call_next: CallNext,
        body: str = rapidy_web.Body(),  # raises HTTPValidationFailure
    ) -> rapidy_web.StreamResponse:
        raise rapidy_web.HTTPInternalServerError(text=TEXT_NOT_CATCH)

    app = rapidy_web.Application(middlewares=[rapidy_validation_errors_catch_middleware, middleware_validation_failure])

    async def handler() -> rapidy_web.Response:
        return rapidy_web.Response(body=TEXT_NOT_CATCH)

    await _test(
        aiohttp_client=aiohttp_client,
        app=app,
        handler=handler,
        expected_text=TEXT_SUCCESS_CATCH_VALIDATION_ERROR,
    )


async def test_success_rapidy_catch_handler_validation_failure(aiohttp_client: AiohttpClient) -> None:
    app = rapidy_web.Application(middlewares=[rapidy_validation_errors_catch_middleware])

    async def handler(
        body: str = rapidy_web.Body(),  # raises HTTPValidationFailure
    ) -> rapidy_web.Response:
        return rapidy_web.Response(body=TEXT_NOT_CATCH)

    await _test(
        aiohttp_client=aiohttp_client,
        app=app,
        handler=handler,
        expected_text=TEXT_SUCCESS_CATCH_VALIDATION_ERROR,
    )


async def test_success_rapidy_catch_aiohttp_not_found(aiohttp_client: AiohttpClient) -> None:
    app = rapidy_web.Application(middlewares=[rapidy_validation_errors_catch_middleware])

    async def handler() -> rapidy_web.Response:
        return rapidy_web.Response(body=TEXT_NOT_CATCH)

    app.add_routes([rapidy_web.post('/', handler)])
    client = await aiohttp_client(app)

    resp = await client.post('/not_found')
    assert resp.status == 200
    resp_text = await resp.text()

    assert resp_text == TEXT_SUCCESS_CATCH_NOT_FOUND_ERROR


async def test_success_rapidy_catch_aiohttp_not_allowed(aiohttp_client: AiohttpClient) -> None:
    app = rapidy_web.Application(middlewares=[rapidy_validation_errors_catch_middleware])

    async def handler() -> rapidy_web.Response:
        return rapidy_web.Response(body=TEXT_NOT_CATCH)

    app.add_routes([rapidy_web.post('/', handler)])
    client = await aiohttp_client(app)

    resp = await client.get('/')
    assert resp.status == 200
    resp_text = await resp.text()

    assert resp_text == TEXT_SUCCESS_CATCH_NOT_ALLOWED_ERROR


async def _test(
    aiohttp_client: AiohttpClient,
    app: Union[aiohttp_web.Application, rapidy_web.Application],
    expected_text: str,
    web_module: Any = rapidy_web,
    handler: Optional[Handler] = None,
) -> None:
    if not handler:

        async def handler(request: web_module.Request) -> web_module.Response:
            return web_module.Response()

    app.add_routes([web_module.post('/', handler)])
    client = await aiohttp_client(app)

    resp = await client.post('/')
    assert resp.status == 200
    resp_text = await resp.text()

    assert resp_text == expected_text
