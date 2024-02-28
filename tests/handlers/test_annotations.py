from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, Optional, Type

import pytest
from pydantic import BaseModel
from pytest_aiohttp.plugin import AiohttpClient
from typing_extensions import Annotated, Final

from rapidy import web
from rapidy.request_params import (
    BytesBody,
    FormDataBody,
    FormDataBodyRaw,
    FormDataBodySchema,
    Header,
    HeaderBase,
    HeaderRaw,
    HeaderSchema,
    JsonBody,
    JsonBodyRaw,
    JsonBodySchema,
    MultipartBody,
    MultipartBodyRaw,
    MultipartBodySchema,
    TextBody,
)

simple_param_checklist = [Header, HeaderSchema, HeaderRaw]
body_checklist = [
    JsonBody,
    JsonBodySchema,
    JsonBodyRaw,
    FormDataBody,
    FormDataBodySchema,
    FormDataBodyRaw,
    MultipartBody,
    MultipartBodySchema,
    MultipartBodyRaw,
    BytesBody,
    TextBody,
]

ATTRIBUTE_DEFINITION_ERR_MSG: Final[str] = 'Error during attribute definition in the handler:'
EXTRACT_SCHEMA_TYPE_ERR_MSG: Final[str] = 'Schema annotated type must be a pydantic.BaseModel or dataclasses.dataclass'


class SchemaPydantic(BaseModel):
    attr: str


@dataclass
class SchemaDataclass:
    attr: str


@pytest.mark.parametrize('type1', simple_param_checklist)
@pytest.mark.parametrize('type2', simple_param_checklist)
async def test_check_simple_param_incorrect_annotations(type1: Type[HeaderBase], type2: Type[HeaderBase]) -> None:
    async def handler(
            request: web.Request,
            attr1: Annotated[SchemaPydantic, type1()],
            attr2: Annotated[SchemaPydantic, type2()],
    ) -> web.Response:
        pass

    if type1().validate_type.is_param() and type2().validate_type.is_param():
        # skip success scenarios
        return

    app = web.Application()

    exc_message = ''
    with pytest.raises(Exception):
        try:
            app.add_routes([web.post('/', handler)])
        except Exception as exc:
            exc_message = exc.args[0]
            raise exc

    assert exc_message.startswith(ATTRIBUTE_DEFINITION_ERR_MSG)


@pytest.mark.parametrize('type1', body_checklist)
@pytest.mark.parametrize('type2', body_checklist)
async def test_check_body_param_incorrect_annotations(type1: Type[Any], type2: Type[Any]) -> None:
    async def handler(
            request: web.Request,
            attr1: Annotated[SchemaPydantic, type1()],
            attr2: Annotated[SchemaPydantic, type2()],
    ) -> web.Response:
        pass

    if type1().validate_type.is_param() and type2().validate_type.is_param():
        # skip success scenarios
        return

    app = web.Application()

    exc_message = ''
    with pytest.raises(Exception):
        try:
            app.add_routes([web.post('/', handler)])
        except Exception as exc:
            exc_message = exc.args[0]
            raise exc

    assert exc_message.startswith(ATTRIBUTE_DEFINITION_ERR_MSG)


@pytest.mark.parametrize(
    'attr_type',
    [
        pytest.param(JsonBody(), id='define-as-instance'),
        pytest.param(JsonBody, id='define-as-class'),
    ],
)
async def test_check_annotation(
        aiohttp_client: AiohttpClient,
        attr_type: Any,
) -> None:
    async def handler(
            request: web.Request,
            attr: Annotated[str, attr_type],
    ) -> web.Response:
        return web.Response()

    app = web.Application()
    app.add_routes([web.post('/', handler)])
    client = await aiohttp_client(app)
    resp = await client.post('/', json={'attr': ''})
    assert resp.status == HTTPStatus.OK


@pytest.mark.parametrize(
    'attr_type',
    [
        SchemaPydantic,
        SchemaDataclass,
        Optional[SchemaPydantic],
        Optional[SchemaDataclass],
    ],
)
async def test_success_schema_annotation(attr_type: Any) -> None:
    async def handler(
            request: web.Request,
            body: Annotated[attr_type, JsonBodySchema],
    ) -> web.Response:
        return web.Response()

    app = web.Application()
    app.add_routes([web.post('/', handler)])


@pytest.mark.parametrize(
    'attr_type',
    [
        JsonBodySchema,
        FormDataBodySchema,
        MultipartBodySchema,
    ],
)
async def test_failed_schema_annotation(attr_type: Any) -> None:
    async def handler(
            request: web.Request,
            body: Annotated[str, attr_type],
    ) -> web.Response:
        pass

    app = web.Application()

    exc_message = ''
    with pytest.raises(Exception):
        try:
            app.add_routes([web.post('/', handler)])
        except Exception as exc:
            exc_message = exc.args[0]
            raise exc

    assert exc_message.startswith(EXTRACT_SCHEMA_TYPE_ERR_MSG)


@pytest.mark.parametrize(
    'attr_type',
    [
        Annotated[str, str],
        Annotated[str, str, str],
    ],
)
async def test_incorrect_rapid_param(aiohttp_client: AiohttpClient, attr_type: Any) -> None:
    async def handler(
            request: web.Request,
            any_param: attr_type,
            body: Annotated[str, str],
    ) -> web.Response:
        pass

    app = web.Application()
    app.add_routes([web.post('/', handler)])

    client = await aiohttp_client(app)
    resp = await client.post('/', json={'attr': ''})

    assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR
