import pytest
from aiohttp.pytest_plugin import AiohttpClient

from rapidy import Rapidy
from rapidy.http import middleware, Request, Response, StreamResponse
from rapidy.typedefs import CallNext
from tests.constants import DEFAULT_RETURN_VALUE


@pytest.mark.parametrize('create_web_response', [True, False])
@pytest.mark.parametrize('return_middleware', [True, False])
async def test_union_stream_response(
    aiohttp_client: AiohttpClient,
    create_web_response: bool,
    return_middleware: bool,
) -> None:
    path = '/'

    async def handler() -> Response | str:
        if create_web_response:
            return Response(DEFAULT_RETURN_VALUE)
        return DEFAULT_RETURN_VALUE

    @middleware
    async def inner_middleware(request: Request, call_next: CallNext) -> StreamResponse | str:
        if return_middleware:
            if create_web_response:
                return Response(DEFAULT_RETURN_VALUE)
            return DEFAULT_RETURN_VALUE
        return await call_next(request)

    rapidy = Rapidy(middlewares=[inner_middleware])
    rapidy.router.add_get(path, handler)

    client = await aiohttp_client(rapidy)
    resp = await client.get(path)

    assert await resp.text() == DEFAULT_RETURN_VALUE
