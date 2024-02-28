from http import HTTPStatus
from typing import Any, Dict, Optional

import pytest
from pydantic import BaseModel
from pytest_aiohttp.plugin import AiohttpClient
from typing_extensions import Annotated

from rapidy import web
from rapidy.request_params import (
    BytesBody,
    Cookie,
    CookieRaw,
    CookieSchema,
    FormDataBody,
    FormDataBodyRaw,
    FormDataBodySchema,
    Header,
    HeaderSchema,
    JsonBody,
    JsonBodyRaw,
    JsonBodySchema,
    MultipartBody,
    MultipartBodyRaw,
    MultipartBodySchema,
    Path,
    Query,
    QueryRaw,
    QuerySchema,
    TextBody,
)
from rapidy.typedefs import HandlerType


class Schema(BaseModel):
    attr1: str


class SchemaWithOneDefaultParam(BaseModel):
    attr1: str = ''
    attr2: str


# NOTE: We do not check the default value type, as this may affect the performance of the whole application at startup.
# Perhaps in a future patch this feature will be added as a toggleable feature.
test_default_values = [
    pytest.param(1, id='int'),
    pytest.param(1.0, id='float'),
    pytest.param('1', id='str'),
    pytest.param((1,), id='tuple'),
    pytest.param(Schema(attr1='1'), id='base-model-instance'),
]


async def test_path_default() -> None:
    async def handler(
            request: web.Request,
            path: Annotated[str, Path(alias='Host')] = '',
    ) -> web.Response:
        pass

    app = web.Application()

    exc_message = ''
    with pytest.raises(AssertionError):
        try:
            app.add_routes([web.post('/', handler)])
        except AssertionError as exc:
            exc_message = exc.args[0]
            raise exc

    assert exc_message.startswith("Handler attribute with Type `Path` cannot have a default value.")


@pytest.mark.parametrize(
    "annotated_type, param_type",
    [
        pytest.param(str, Header, id='header-param'),
        pytest.param(str, Cookie, id='cookie-param'),
        pytest.param(str, Query, id='query-param'),
        pytest.param(str, JsonBody, id='body-json-param'),
        pytest.param(str, FormDataBody, id='body-form-data-param'),
        pytest.param(str, MultipartBody, id='body-multipart'),
        pytest.param(Schema, CookieSchema, id='cookie-schema'),
        pytest.param(Schema, QuerySchema, id='query-schema'),
        pytest.param(Schema, JsonBodySchema, id='body-json-schema'),
        pytest.param(Schema, FormDataBodySchema, id='body-form-data-schema'),
        pytest.param(Schema, MultipartBodySchema, id='body-multipart-schema'),
        pytest.param(Dict[str, Any], CookieRaw, id='cookie-raw'),
        pytest.param(Dict[str, Any], QueryRaw, id='query-raw'),
        pytest.param(Dict[str, Any], JsonBodyRaw, id='body-json-raw'),
        pytest.param(Dict[str, Any], FormDataBodyRaw, id='body-form-data-raw'),
        pytest.param(Dict[str, Any], MultipartBodyRaw, id='body-multipart-raw'),
        pytest.param(str, TextBody, id='body-text'),
        pytest.param(bytes, BytesBody, id='body-bytes'),
    ],
)
@pytest.mark.parametrize("default_value", test_default_values)
async def test_default(
        aiohttp_client: AiohttpClient,
        annotated_type: Any,
        param_type: Any,
        default_value: Any,
) -> None:
    async def handler(
            request: web.Request,
            data: Annotated[annotated_type, param_type] = default_value,
    ) -> web.Response:
        assert data == default_value
        return web.Response()

    await _test(aiohttp_client, handler, {}, HTTPStatus.OK)


@pytest.mark.parametrize(
    "annotated_type, param_type, expected_data",
    [
        pytest.param(str, Header, None, id='header-param'),
        pytest.param(str, Cookie, None, id='cookie-param'),
        pytest.param(str, Query, None, id='query-param'),
        pytest.param(str, JsonBody, None, id='body-json-param'),
        pytest.param(str, FormDataBody, None, id='body-form-data-param'),
        pytest.param(str, MultipartBody, None, id='body-multipart-param'),
        pytest.param(Schema, CookieSchema, None, id='cookie-schema'),
        pytest.param(Schema, QuerySchema, None, id='query-schema'),
        pytest.param(Schema, JsonBodySchema, None, id='body-json-schema'),
        pytest.param(Schema, FormDataBodySchema, None, id='body-form-data-schema'),
        pytest.param(Schema, MultipartBodySchema, None, id='body-multipart-schema'),
        pytest.param(Dict[str, Any], CookieRaw, {}, id='cookie-raw'),
        pytest.param(Dict[str, Any], QueryRaw, {}, id='query-raw'),
        pytest.param(Dict[str, Any], JsonBodyRaw, {}, id='body-json-raw'),
        pytest.param(Dict[str, Any], FormDataBodyRaw, {}, id='body-form-data-raw'),
        pytest.param(Dict[str, Any], MultipartBodyRaw, {}, id='body-multipart-raw'),
        pytest.param(str, TextBody, '', id='body-text'),
        pytest.param(bytes, BytesBody, b'', id='body-bytes'),
    ],
)
async def test_optional(
        aiohttp_client: AiohttpClient,
        annotated_type: Any,
        param_type: Any,
        expected_data: Any,
) -> None:
    async def handler(
            request: web.Request,
            data: Annotated[Optional[annotated_type], param_type] = None,
    ) -> web.Response:
        assert data == expected_data
        return web.Response()

    await _test(aiohttp_client, handler, {}, HTTPStatus.OK)


@pytest.mark.parametrize(
    "annotated_type, param_type, expected_data, resp_code",
    [
        pytest.param(str, Cookie, None, HTTPStatus.UNPROCESSABLE_ENTITY, id='cookie-param'),
        pytest.param(str, Query, None, HTTPStatus.UNPROCESSABLE_ENTITY, id='query-param'),
        pytest.param(str, JsonBody, None, HTTPStatus.UNPROCESSABLE_ENTITY, id='body-json-param'),
        pytest.param(str, FormDataBody, None, HTTPStatus.UNPROCESSABLE_ENTITY, id='body-form-data-param'),
        pytest.param(str, MultipartBody, None, HTTPStatus.UNPROCESSABLE_ENTITY, id='body-multipart-param'),
        pytest.param(Schema, CookieSchema, None, HTTPStatus.UNPROCESSABLE_ENTITY, id='header-schema'),
        pytest.param(Schema, QuerySchema, None, HTTPStatus.UNPROCESSABLE_ENTITY, id='query-schema'),
        pytest.param(Schema, JsonBodySchema, None, HTTPStatus.UNPROCESSABLE_ENTITY, id='body-json-schema'),
        pytest.param(Schema, FormDataBodySchema, None, HTTPStatus.UNPROCESSABLE_ENTITY, id='body-form-data-schema'),
        pytest.param(Schema, MultipartBodySchema, None, HTTPStatus.UNPROCESSABLE_ENTITY, id='body-multipart-schema'),
        pytest.param(Dict[str, Any], CookieRaw, {}, HTTPStatus.OK, id='cookie-raw'),
        pytest.param(Dict[str, Any], QueryRaw, {}, HTTPStatus.OK, id='query-raw'),
        pytest.param(Dict[str, Any], JsonBodyRaw, {}, HTTPStatus.OK, id='body-json-raw'),
        pytest.param(Dict[str, Any], FormDataBodyRaw, {}, HTTPStatus.OK, id='body-form-data-raw'),
        pytest.param(Dict[str, Any], MultipartBodyRaw, {}, HTTPStatus.OK, id='body-multipart-raw'),
        pytest.param(str, TextBody, '', HTTPStatus.OK,id='body-text'),
        pytest.param(bytes, BytesBody, b'', HTTPStatus.OK, id='body-bytes'),
    ],
)
async def test_attrs_no_values_no_default(
        aiohttp_client: AiohttpClient,
        annotated_type: Any,
        param_type: Any,
        resp_code: HTTPStatus,
        expected_data: Any,
) -> None:
    async def handler(
            request: web.Request,
            data: Annotated[annotated_type, param_type],
    ) -> web.Response:
        assert data == expected_data
        return web.Response()

    await _test(aiohttp_client, handler, {}, resp_code)


@pytest.mark.parametrize(
    "param_type, request_kw",
    [
        [HeaderSchema, {'headers': {'attr2': 'attr2'}}],
        [CookieSchema, {'cookies': {'attr2': 'attr2'}}],
        [QuerySchema, {'params': {'attr2': 'attr2'}}],
        [JsonBodySchema, {'json': {'attr2': 'attr2'}}],
        [FormDataBodySchema, {'data': {'attr2': 'attr2'}}],
    ],
)
async def test_attrs_schema_one_param_exist_second_param_is_default(
        aiohttp_client: AiohttpClient,
        param_type: Any,
        request_kw: Dict[str, Any],
) -> None:
    async def handler(
            request: web.Request,
            schema: Annotated[SchemaWithOneDefaultParam, param_type],
    ) -> web.Response:
        assert schema == SchemaWithOneDefaultParam(attr2='attr2')
        return web.Response()

    await _test(aiohttp_client, handler, request_kw, HTTPStatus.OK)


async def _test(
        aiohttp_client: AiohttpClient,
        handler: HandlerType,
        request_kw: Dict[str, Any],
        resp_status: int,
) -> None:
    app = web.Application()
    app.add_routes([web.post('/', handler)])
    client = await aiohttp_client(app)
    resp = await client.post('/', **request_kw)
    assert resp.status == resp_status
