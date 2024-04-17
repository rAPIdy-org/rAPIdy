from http import HTTPStatus
from typing import Any

import pytest
from aiohttp import MultipartWriter
from multidict import MultiDict
from pydantic import BaseModel
from pytest_aiohttp.plugin import AiohttpClient
from typing_extensions import Annotated

from rapidy import web
from rapidy.request_params import (
    BodyParamAttrDefinitionError,
    BytesBody,
    FormDataBody,
    FormDataBodyRaw,
    FormDataBodySchema,
    JsonBody,
    JsonBodyRaw,
    JsonBodySchema,
    MultipartBody,
    MultipartBodyRaw,
    MultipartBodySchema,
    TextBody,
)


class Schema(BaseModel):
    pass


@pytest.mark.parametrize(
    'body_type',
    [
        TextBody,
        BytesBody,
        JsonBodySchema,
        JsonBodyRaw,
        FormDataBodySchema,
        FormDataBodyRaw,
    ],
)
async def test_body_size_exceeded(aiohttp_client: AiohttpClient, body_type: Any) -> None:
    async def handler(
            param: Annotated[Schema, body_type(body_max_size=1)],
    ) -> web.Response:
        return web.Response()

    app = web.Application()
    app.add_routes([web.post('/', handler)])
    client = await aiohttp_client(app)
    resp = await client.post('/', data='{}')
    assert resp.status == HTTPStatus.UNPROCESSABLE_ENTITY
    resp_json = await resp.json()
    assert resp_json == {
        'errors': [
            {
                'loc': ['body'],
                'msg': 'Failed to extract body data. Body data exceeds the allowed size `1`',
                'type': 'body_extraction',
            },
        ],
    }


@pytest.mark.parametrize(
    'body_type',
    [
        MultipartBodySchema,
        MultipartBodyRaw,
    ],
)
async def test_body_size_exceeded_multipart(
        aiohttp_client: AiohttpClient,
        body_type: Any,
        form_data_disptype_name: str,
        content_type_text_header: MultiDict[str],
        multipart_writer: MultipartWriter,
) -> None:
    async def handler(
            param: Annotated[Schema, body_type(body_max_size=1)],
    ) -> web.Response:
        return web.Response()

    app = web.Application()
    app.add_routes([web.post('/', handler)])
    client = await aiohttp_client(app)

    part = multipart_writer.append("10", content_type_text_header)
    part.set_content_disposition(form_data_disptype_name, name="attr1")

    resp = await client.post('/', data=multipart_writer)

    assert resp.status == HTTPStatus.UNPROCESSABLE_ENTITY
    resp_json = await resp.json()
    assert resp_json == {
        'errors': [
            {
                'loc': ['body'],
                'msg': 'Failed to extract body data. Body data exceeds the allowed size `1`',
                'type': 'body_extraction',
            },
        ],
    }


@pytest.mark.parametrize(
    'body_type',
    [
        JsonBody,
        FormDataBody,
        MultipartBody,
    ],
)
async def test_failure_def_body_size_to_param(body_type: Any) -> None:
    with pytest.raises(BodyParamAttrDefinitionError):
        body_type(body_max_size=1)


@pytest.mark.parametrize(
    'body_type',
    [
        JsonBodySchema,
        JsonBodyRaw,
    ],
)
async def test_success_custom_def_json_decoder(body_type: Any) -> None:
    body_type(json_decoder=lambda: 1)


async def test_failure_custom_def_json_decoder() -> None:
    with pytest.raises(BodyParamAttrDefinitionError):
        JsonBody(json_decoder=lambda: 1)


@pytest.mark.parametrize(
    'body_type',
    [
        FormDataBodySchema,
        FormDataBodyRaw,
        MultipartBodySchema,
        MultipartBodyRaw,
    ],
)
@pytest.mark.parametrize(
    'kw',
    [
        {'attrs_case_sensitive': True},
        {'duplicated_attrs_parse_as_array': True},
    ],
)
async def test_success_form_specified_attrs(body_type: Any, kw: Any) -> None:
    body_type(**kw)


@pytest.mark.parametrize(
    'body_type',
    [
        FormDataBody,
        MultipartBody,
    ],
)
@pytest.mark.parametrize(
    'kw',
    [
        {'attrs_case_sensitive': True},
        {'duplicated_attrs_parse_as_array': True},
    ],
)
async def test_failure_form_specified_attrs(body_type: Any, kw: Any) -> None:
    with pytest.raises(BodyParamAttrDefinitionError):
        body_type(**kw)
