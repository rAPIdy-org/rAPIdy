from typing import Final

import pytest

from rapidy import Rapidy
from rapidy.http import (
    Body,
    HTTPInternalServerError,
    HTTPMethodNotAllowed,
    HTTPNotFound,
    HTTPOk,
    HTTPUnprocessableEntity,
    HTTPValidationFailure,
    middleware,
    post,
    Request,
    Response,
    StreamResponse,
)
from rapidy.typedefs import CallNext, Handler
from tests.ported.client import AppClientFactory

TEXT_SUCCESS_CATCH_OK: Final[str] = 'ok'
TEXT_SUCCESS_CATCH_UNPROCESSABLE_ENTITY: Final[str] = 'unprocessable_entity'
TEXT_SUCCESS_CATCH_NOT_FOUND_ERROR: Final[str] = 'not_found_error'
TEXT_SUCCESS_CATCH_NOT_ALLOWED_ERROR: Final[str] = 'not_allowed_error'
TEXT_SUCCESS_CATCH_VALIDATION_ERROR: Final[str] = 'success_validation_error'
TEXT_NOT_CATCH: Final[str] = 'not_catch'


def errors_catch_middleware(*, marked: bool) -> Handler:
    async def inner(request: Request, call_next: CallNext) -> StreamResponse:
        try:
            return await call_next(request)
        except HTTPOk:
            return Response(body=TEXT_SUCCESS_CATCH_OK)
        except HTTPUnprocessableEntity:
            return Response(body=TEXT_SUCCESS_CATCH_UNPROCESSABLE_ENTITY)
        except Exception:
            return Response(body=TEXT_NOT_CATCH)

    return middleware(inner) if marked else inner


@middleware
async def rapidy_validation_errors_catch_middleware(
    request: Request,
    call_next: CallNext,
) -> StreamResponse:
    try:
        return await call_next(request)
    except HTTPNotFound:
        return Response(body=TEXT_SUCCESS_CATCH_NOT_FOUND_ERROR)
    except HTTPMethodNotAllowed:
        return Response(body=TEXT_SUCCESS_CATCH_NOT_ALLOWED_ERROR)
    except HTTPValidationFailure:
        return Response(body=TEXT_SUCCESS_CATCH_VALIDATION_ERROR)
    except Exception:
        return Response(body=TEXT_NOT_CATCH)


@pytest.mark.parametrize(
    'marked_inner',
    [pytest.param(False, id='raw-middleware'), pytest.param(True, id='marked-middleware')],
)
@pytest.mark.parametrize(
    'marked_outer',
    [pytest.param(False, id='raw-catcher'), pytest.param(True, id='marked-catcher')],
)
async def test_raw_and_marked_middleware(
    app_client: AppClientFactory,
    marked_outer: bool,
    marked_inner: bool,
) -> None:
    async def middleware_manually_raise_error(
        request: Request,
        call_next: CallNext,
    ) -> StreamResponse:
        raise HTTPOk(text=TEXT_SUCCESS_CATCH_OK)

    inner = middleware(middleware_manually_raise_error) if marked_inner else middleware_manually_raise_error
    app = Rapidy(
        middlewares=[errors_catch_middleware(marked=marked_outer), inner],
    )
    await _test(app_client=app_client, app=app, expected_text=TEXT_SUCCESS_CATCH_OK)


@pytest.mark.parametrize('marked', [False, True])
async def test_success_catch_unprocessable_entity_with_rapidy_middleware_validation(
    app_client: AppClientFactory,
    marked: bool,
) -> None:
    @middleware
    async def middleware_validation_failure(
        request: Request,
        handler: CallNext,
        body: str = Body(),  # raises HTTPValidationFailure
    ) -> StreamResponse:
        raise HTTPInternalServerError(text=TEXT_NOT_CATCH)

    app = Rapidy(
        middlewares=[errors_catch_middleware(marked=marked), middleware_validation_failure],
    )
    await _test(app_client=app_client, app=app, expected_text=TEXT_SUCCESS_CATCH_UNPROCESSABLE_ENTITY)


async def test_success_catch_unprocessable_entity_with_rapidy_handler_validation(app_client: AppClientFactory) -> None:
    app = Rapidy(middlewares=[errors_catch_middleware(marked=True)])

    async def handler(
        body: str = Body(),  # raises HTTPValidationFailure
    ) -> Response:
        return Response(body=TEXT_NOT_CATCH)

    await _test(
        app_client=app_client,
        app=app,
        handler=handler,
        expected_text=TEXT_SUCCESS_CATCH_UNPROCESSABLE_ENTITY,
    )


async def test_success_rapidy_catch_middleware_validation_failure(app_client: AppClientFactory) -> None:
    @middleware
    async def middleware_validation_failure(
        request: Request,
        call_next: CallNext,
        body: str = Body(),  # raises HTTPValidationFailure
    ) -> StreamResponse:
        raise HTTPInternalServerError(text=TEXT_NOT_CATCH)

    app = Rapidy(middlewares=[rapidy_validation_errors_catch_middleware, middleware_validation_failure])

    async def handler() -> Response:
        return Response(body=TEXT_NOT_CATCH)

    await _test(
        app_client=app_client,
        app=app,
        handler=handler,
        expected_text=TEXT_SUCCESS_CATCH_VALIDATION_ERROR,
    )


async def test_success_rapidy_catch_handler_validation_failure(app_client: AppClientFactory) -> None:
    app = Rapidy(middlewares=[rapidy_validation_errors_catch_middleware])

    async def handler(
        body: str = Body(),  # raises HTTPValidationFailure
    ) -> Response:
        return Response(body=TEXT_NOT_CATCH)

    await _test(
        app_client=app_client,
        app=app,
        handler=handler,
        expected_text=TEXT_SUCCESS_CATCH_VALIDATION_ERROR,
    )


async def test_success_rapidy_catch_not_found(app_client: AppClientFactory) -> None:
    app = Rapidy(middlewares=[rapidy_validation_errors_catch_middleware])

    async def handler() -> Response:
        return Response(body=TEXT_NOT_CATCH)

    app.add_http_router(post.reg('/', handler))
    client = await app_client(app)

    resp = await client.post('/not_found')
    assert resp.status == 200
    resp_text = await resp.text()

    assert resp_text == TEXT_SUCCESS_CATCH_NOT_FOUND_ERROR


async def test_success_rapidy_catch_not_allowed(app_client: AppClientFactory) -> None:
    app = Rapidy(middlewares=[rapidy_validation_errors_catch_middleware])

    async def handler() -> Response:
        return Response(body=TEXT_NOT_CATCH)

    app.add_http_router(post.reg('/', handler))
    client = await app_client(app)

    resp = await client.get('/')
    assert resp.status == 200
    resp_text = await resp.text()

    assert resp_text == TEXT_SUCCESS_CATCH_NOT_ALLOWED_ERROR


async def _test(
    app_client: AppClientFactory,
    app: Rapidy,
    expected_text: str,
    handler: Handler | None = None,
) -> None:
    if not handler:

        async def handler(request: Request) -> Response:
            return Response()

    app.add_http_router(post.reg('/', handler))
    client = await app_client(app)

    resp = await client.post('/')
    assert resp.status == 200
    resp_text = await resp.text()

    assert resp_text == expected_text
