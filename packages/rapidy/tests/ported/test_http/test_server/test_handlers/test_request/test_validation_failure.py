from http import HTTPStatus
from typing import Any
from typing_extensions import Annotated, Final

from pydantic import BaseModel, Field
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
from rapidy.http import post, Response
from rapidy.typedefs import HandlerOrView
from tests.ported.client import AppClientFactory

HANDLER_PATH: Final[str] = '/{attr1}/{attr2}/{attr3}'

REQUEST = {'attr1': '0', 'attr2': '0', 'attr3': '0'}
REQUEST_PATH: Final[str] = HANDLER_PATH.format(**REQUEST)


attr1_model_field_args = {
    'alias': 'attr1',
    'min_length': 2,
}
attr2_model_field_args = {
    'alias': 'attr2',
    'ge': 1,
}
attr3_model_field_args = {
    'alias': 'attr3',
    'min_items': 1,
}
attr4_model_field_args = {
    'alias': 'attr4',
}


class Schema(BaseModel):
    attr1: str = Field(**attr1_model_field_args)
    attr2: int = Field(**attr2_model_field_args)
    attr3: list[str] = Field(**attr3_model_field_args)
    attr4: str = Field(**attr4_model_field_args)


async def test_individual_params(app_client: AppClientFactory) -> None:
    async def handler(  # noqa: PLR0917 - parity exercises all validation locations together
        path_attr1: Annotated[str, PathParam(**attr1_model_field_args)],
        path_attr2: Annotated[int, PathParam(**attr2_model_field_args)],
        path_attr3: Annotated[list[int], PathParam(**attr3_model_field_args)],
        path_attr4: Annotated[str, PathParam(**attr4_model_field_args)],
        header_attr1: Annotated[str, Header(**attr1_model_field_args)],
        header_attr2: Annotated[int, Header(**attr2_model_field_args)],
        header_attr3: Annotated[list[int], Header(**attr3_model_field_args)],
        header_attr4: Annotated[str, Header(**attr4_model_field_args)],
        cookie_attr1: Annotated[str, Cookie(**attr1_model_field_args)],
        cookie_attr2: Annotated[int, Cookie(**attr2_model_field_args)],
        cookie_attr3: Annotated[list[int], Cookie(**attr3_model_field_args)],
        cookie_attr4: Annotated[str, Cookie(**attr4_model_field_args)],
        query_attr1: Annotated[str, QueryParam(**attr1_model_field_args)],
        query_attr2: Annotated[int, QueryParam(**attr2_model_field_args)],
        query_attr3: Annotated[list[int], QueryParam(**attr3_model_field_args)],
        query_attr4: Annotated[str, QueryParam(**attr4_model_field_args)],
        body_data: Annotated[Schema, Body()],
    ) -> Response:
        return Response()

    await _test(app_client, handler)


async def test_single_schema(app_client: AppClientFactory) -> None:
    async def handler(
        path_data: Annotated[Schema, PathParams()],
        header_data: Annotated[Schema, Headers()],
        cookie_data: Annotated[Schema, Cookies()],
        query_data: Annotated[Schema, QueryParams()],
        body_data: Annotated[Schema, Body()],
    ) -> Response:
        return Response()

    await _test(app_client, handler)


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
    assert resp.status == HTTPStatus.UNPROCESSABLE_ENTITY
    resp_json = await resp.json()

    pydantic_v2_err_check(resp_json)


def pydantic_v2_err_check(resp_json: dict[str, Any]) -> None:
    assert resp_json == {
        'errors': [
            {
                'ctx': {'min_length': 2},
                'loc': ['path', 'attr1'],
                'msg': 'String should have at least 2 characters',
                'type': 'string_too_short',
            },
            {
                'ctx': {'ge': 1},
                'loc': ['path', 'attr2'],
                'msg': 'Input should be greater than or equal to 1',
                'type': 'greater_than_equal',
            },
            {
                'loc': ['path', 'attr3'],
                'msg': 'Input should be a valid list',
                'type': 'list_type',
            },
            {
                'loc': ['path', 'attr4'],
                'msg': 'Field required',
                'type': 'missing',
            },
            {
                'ctx': {'min_length': 2},
                'loc': ['header', 'attr1'],
                'msg': 'String should have at least 2 characters',
                'type': 'string_too_short',
            },
            {
                'ctx': {'ge': 1},
                'loc': ['header', 'attr2'],
                'msg': 'Input should be greater than or equal to 1',
                'type': 'greater_than_equal',
            },
            {
                'loc': ['header', 'attr3'],
                'msg': 'Input should be a valid list',
                'type': 'list_type',
            },
            {
                'loc': ['header', 'attr4'],
                'msg': 'Field required',
                'type': 'missing',
            },
            {
                'ctx': {'min_length': 2},
                'loc': ['cookie', 'attr1'],
                'msg': 'String should have at least 2 characters',
                'type': 'string_too_short',
            },
            {
                'ctx': {'ge': 1},
                'loc': ['cookie', 'attr2'],
                'msg': 'Input should be greater than or equal to 1',
                'type': 'greater_than_equal',
            },
            {
                'loc': ['cookie', 'attr3'],
                'msg': 'Input should be a valid list',
                'type': 'list_type',
            },
            {
                'loc': ['cookie', 'attr4'],
                'msg': 'Field required',
                'type': 'missing',
            },
            {
                'ctx': {'min_length': 2},
                'loc': ['query', 'attr1'],
                'msg': 'String should have at least 2 characters',
                'type': 'string_too_short',
            },
            {
                'ctx': {'ge': 1},
                'loc': ['query', 'attr2'],
                'msg': 'Input should be greater than or equal to 1',
                'type': 'greater_than_equal',
            },
            {
                'loc': ['query', 'attr3'],
                'msg': 'Input should be a valid list',
                'type': 'list_type',
            },
            {
                'loc': ['query', 'attr4'],
                'msg': 'Field required',
                'type': 'missing',
            },
            {
                'ctx': {'min_length': 2},
                'loc': ['body', 'attr1'],
                'msg': 'String should have at least 2 characters',
                'type': 'string_too_short',
            },
            {
                'ctx': {'ge': 1},
                'loc': ['body', 'attr2'],
                'msg': 'Input should be greater than or equal to 1',
                'type': 'greater_than_equal',
            },
            {
                'loc': ['body', 'attr3'],
                'msg': 'Input should be a valid list',
                'type': 'list_type',
            },
            {
                'loc': ['body', 'attr4'],
                'msg': 'Field required',
                'type': 'missing',
            },
        ],
    }
