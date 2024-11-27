from http import HTTPStatus
from typing import Any, Dict, Type, Union

import pytest
from aiohttp.pytest_plugin import AiohttpClient
from pydantic import BaseModel

from rapidy import web
from rapidy.constants import PYDANTIC_IS_V1
from rapidy.parameters.http import QueryParam, QueryParams


class SchemaA(BaseModel):
    a: int


class SchemaB(BaseModel):
    b: int


@pytest.mark.parametrize(
    'annotation, param_type, params, expected_type_pydantic_v1, expected_type_pydantic_v2', (
        (Union[int, str], QueryParam, {'p': 1}, int, str),
        (Union[int, str], QueryParam, {'p': '1'}, int, str),
        (Union[int, str], QueryParam, {'p': '1s'}, str, str),
        (Union[SchemaA, SchemaB], QueryParams, {'a': 1}, SchemaA, SchemaA),
        (Union[SchemaA, SchemaB], QueryParams, {'b': 1}, SchemaB, SchemaB),
    ),
)
async def test_union_datatype(
        annotation: Any,
        param_type: Any,
        aiohttp_client: AiohttpClient,
        params: Dict[str, Any],
        expected_type_pydantic_v1: Type[Any],
        expected_type_pydantic_v2: Type[Any],
) -> None:
    async def handler(p: annotation = param_type()) -> web.Response:
        if PYDANTIC_IS_V1:
            assert isinstance(p, expected_type_pydantic_v1)
        else:
            assert isinstance(p, expected_type_pydantic_v2)
        return web.Response()

    app = web.Application()
    app.add_routes([web.post('/', handler)])

    client = await aiohttp_client(app)
    resp = await client.post('/', params=params)

    assert resp.status == HTTPStatus.OK
