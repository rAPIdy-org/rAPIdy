from http import HTTPStatus
from typing import Any

from pydantic import BaseModel
from pytest_aiohttp.plugin import AiohttpClient
from typing_extensions import Annotated, Final

from rapidy import web
from rapidy.parameters.http import (
    Body,
    Cookie,
    Cookies,
    Header,
    Headers,
    PathParam,
    PathParams,
    QueryParam,
    QueryParams,
)
from rapidy.typedefs import HandlerOrView

HANDLER_PATH: Final[str] = '/{attr1}/{attr2}'

REQUEST = {'attr1': '1', 'attr2': '2'}
REQUEST_PATH: Final[str] = HANDLER_PATH.format(**REQUEST)


class Schema(BaseModel):
    attr1: int
    attr2: int


async def test_params(aiohttp_client: AiohttpClient) -> None:
    async def handler_annotated_param_def(
            path_attr1: Annotated[int, PathParam(alias='attr1')],
            path_attr2: Annotated[int, PathParam(alias='attr2')],
            header_attr1: Annotated[int, Header(alias='attr1')],
            header_attr2: Annotated[int, Header(alias='attr2')],
            cookie_attr1: Annotated[int, Cookie(alias='attr1')],
            cookie_attr2: Annotated[int, Cookie(alias='attr2')],
            query_attr1: Annotated[int, QueryParam(alias='attr1')],
            query_attr2: Annotated[int, QueryParam(alias='attr2')],
    ) -> None:
        _check_sequence_data_type(
            path_attr1, header_attr1, cookie_attr1, query_attr1,
            path_attr2, header_attr2, cookie_attr2, query_attr2,
            expected_type=int,
        )
        _check_sequence_data_type( expected_type=str)
        pass

    async def handler_default_param_def(
            path_attr1: int = PathParam(alias='attr1'),
            path_attr2: int = PathParam(alias='attr2'),
            header_attr1: int = Header(alias='attr1'),
            header_attr2: int = Header(alias='attr2'),
            cookie_attr1: int = Cookie(alias='attr1'),
            cookie_attr2: int = Cookie(alias='attr2'),
            query_attr1: int = QueryParam(alias='attr1'),
            query_attr2: int = QueryParam(alias='attr2'),
    ) -> None:
        _check_sequence_data_type(
            path_attr1, header_attr1, cookie_attr1, query_attr1,
            path_attr2, header_attr2, cookie_attr2, query_attr2,
            expected_type=int,
        )
        pass

    await _test(aiohttp_client, handler_annotated_param_def)
    await _test(aiohttp_client, handler_default_param_def)


async def test_all(aiohttp_client: AiohttpClient) -> None:
    async def handler_annotated_param_def(
            path_data: Annotated[Schema, PathParams()],
            header_data: Annotated[Schema, Headers()],
            cookie_data: Annotated[Schema, Cookies()],
            query_data: Annotated[Schema, QueryParams()],
            body_data: Annotated[Schema, Body()],
    ) -> None:
        pass

    async def handler_default_param_def(
            path_data: Schema = PathParams(),
            header_data: Schema = Headers(),
            cookie_data: Schema = Cookies(),
            query_data: Schema = QueryParams(),
            body_data: Schema = Body(),
    ) -> None:
        pass

    await _test(aiohttp_client, handler_annotated_param_def)
    await _test(aiohttp_client, handler_default_param_def)


def _check_sequence_data_type(*params: Any, expected_type: Any) -> None:
    for data in params:
        assert type(data) == expected_type


async def _test(aiohttp_client: AiohttpClient, handler: HandlerOrView) -> None:
    app = web.Application()
    app.add_routes([web.post(HANDLER_PATH, handler)])
    client = await aiohttp_client(app)
    resp = await client.post(
        REQUEST_PATH,
        json=REQUEST,
        cookies=REQUEST,
        headers=REQUEST,
        params=REQUEST,
    )
    assert resp.status == HTTPStatus.OK
