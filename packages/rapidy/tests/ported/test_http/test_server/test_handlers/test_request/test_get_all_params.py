from http import HTTPStatus
from typing import Any
from typing_extensions import Annotated, Final

from pydantic import BaseModel
from rapidy_core.parameters.http import (
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

from rapidy import Rapidy
from rapidy.http import post
from rapidy.typedefs import HandlerOrView
from tests.ported.client import AppClientFactory

HANDLER_PATH: Final[str] = '/{attr1}/{attr2}'

REQUEST = {'attr1': '1', 'attr2': '2'}
REQUEST_PATH: Final[str] = HANDLER_PATH.format(**REQUEST)


class Schema(BaseModel):
    attr1: int
    attr2: int


async def test_params(app_client: AppClientFactory) -> None:
    async def handler_annotated_param_def(  # noqa: PLR0917 - parity exercises all parameter sources together
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
            path_attr1,
            header_attr1,
            cookie_attr1,
            query_attr1,
            path_attr2,
            header_attr2,
            cookie_attr2,
            query_attr2,
            expected_type=int,
        )
        _check_sequence_data_type(expected_type=str)

    async def handler_default_param_def(  # noqa: PLR0917 - parity exercises all parameter sources together
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
            path_attr1,
            header_attr1,
            cookie_attr1,
            query_attr1,
            path_attr2,
            header_attr2,
            cookie_attr2,
            query_attr2,
            expected_type=int,
        )

    await _test(app_client, handler_annotated_param_def)
    await _test(app_client, handler_default_param_def)


async def test_all(app_client: AppClientFactory) -> None:
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

    await _test(app_client, handler_annotated_param_def)
    await _test(app_client, handler_default_param_def)


def _check_sequence_data_type(*params: Any, expected_type: Any) -> None:
    for data in params:
        assert type(data) == expected_type  # noqa: E721


async def _test(app_client: AppClientFactory, handler: HandlerOrView) -> None:
    app = Rapidy(http_route_handlers=[post.reg(HANDLER_PATH, handler)])
    client = await app_client(app)
    resp = await client.post(
        REQUEST_PATH,
        json=REQUEST,
        cookies=REQUEST,
        headers=REQUEST,
        params=REQUEST,
    )
    assert resp.status == HTTPStatus.OK
