from http import HTTPStatus
from typing import Any, Dict

import pytest
from aiohttp.web_routedef import RouteTableDef
from pydantic import BaseModel
from pytest import param
from pytest_aiohttp.plugin import AiohttpClient
from typing_extensions import Annotated

from rapidy import web
from rapidy.request_params import (
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
    Query,
    QueryRaw,
    QuerySchema,
)
from rapidy.web import Application


class Schema(BaseModel):
    attr: str


@pytest.mark.parametrize(
    "annotated_type, param_type, request_kw, expected_data",
    [
        param(str, Header, {'headers': {'attr': 'attr'}}, 'attr', id='header-param'),
        param(str, Cookie, {'cookies': {'attr': 'attr'}}, 'attr', id='cookie-param'),
        param(str, Query, {'params': {'attr': 'attr'}}, 'attr', id='query-param'),
        param(str, JsonBody, {'json': {'attr': 'attr'}}, 'attr', id='body-json-param'),
        param(str, FormDataBody, {'data': {'attr': 'attr'}}, 'attr', id='body-form-data-param'),
        param(Schema, HeaderSchema, {'headers': {'attr': 'attr'}}, Schema(attr='attr'), id='header-schema'),
        param(Schema, CookieSchema, {'cookies': {'attr': 'attr'}}, Schema(attr='attr'), id='cookie-schema'),
        param(Schema, QuerySchema, {'params': {'attr': 'attr'}}, Schema(attr='attr'), id='query-schema'),
        param(Schema, JsonBodySchema, {'json': {'attr': 'attr'}}, Schema(attr='attr'), id='body-json-schema'),
        param(Schema, FormDataBodySchema, {'data': {'attr': 'attr'}}, Schema(attr='attr'), id='body-form-schema'),
        param(Dict[str, Any], CookieRaw, {'cookies': {'attr': 'attr'}}, {'attr': 'attr'}, id='cookie-raw'),
        param(Dict[str, Any], QueryRaw, {'params': {'attr': 'attr'}}, {'attr': 'attr'}, id='query-raw'),
        param(Dict[str, Any], JsonBodyRaw, {'json': {'attr': 'attr'}}, {'attr': 'attr'}, id='body-json-raw'),
        param(Dict[str, Any], FormDataBodyRaw, {'data': {'attr': 'attr'}}, {'attr': 'attr'}, id='body-form-data-raw'),
    ],
)
async def test_success_class_def_as_different_methods(
        aiohttp_client: AiohttpClient,
        annotated_type: Any,
        param_type: Any,
        request_kw: Dict[str, Any],
        expected_data: Any,
) -> None:
    handler = _create_class_handler(annotated_type, param_type, expected_data)

    app = Application()
    app.add_routes([web.post('/', handler), web.put('/', handler)])

    await _test(aiohttp_client, app, request_kw)


@pytest.mark.parametrize(
    "annotated_type, param_type, request_kw, expected_data",
    [
        param(str, Header, {'headers': {'attr': 'attr'}}, 'attr', id='header-param'),
        param(str, Cookie, {'cookies': {'attr': 'attr'}}, 'attr', id='cookie-param'),
        param(str, Query, {'params': {'attr': 'attr'}}, 'attr', id='query-param'),
        param(str, JsonBody, {'json': {'attr': 'attr'}}, 'attr', id='body-json-param'),
        param(str, FormDataBody, {'data': {'attr': 'attr'}}, 'attr', id='body-form-data-param'),
        param(Schema, HeaderSchema, {'headers': {'attr': 'attr'}}, Schema(attr='attr'), id='header-schema'),
        param(Schema, CookieSchema, {'cookies': {'attr': 'attr'}}, Schema(attr='attr'), id='cookie-schema'),
        param(Schema, QuerySchema, {'params': {'attr': 'attr'}}, Schema(attr='attr'), id='query-schema'),
        param(Schema, JsonBodySchema, {'json': {'attr': 'attr'}}, Schema(attr='attr'), id='body-json-schema'),
        param(Schema, FormDataBodySchema, {'data': {'attr': 'attr'}}, Schema(attr='attr'), id='body-form-schema'),
        param(Dict[str, Any], CookieRaw, {'cookies': {'attr': 'attr'}}, {'attr': 'attr'}, id='cookie-raw'),
        param(Dict[str, Any], QueryRaw, {'params': {'attr': 'attr'}}, {'attr': 'attr'}, id='query-raw'),
        param(Dict[str, Any], JsonBodyRaw, {'json': {'attr': 'attr'}}, {'attr': 'attr'}, id='body-json-raw'),
        param(Dict[str, Any], FormDataBodyRaw, {'data': {'attr': 'attr'}}, {'attr': 'attr'}, id='body-form-data-raw'),
    ],
)
async def test_success_func_def(
        aiohttp_client: AiohttpClient,
        annotated_type: Any,
        param_type: Any,
        request_kw: Dict[str, Any],
        expected_data: Any,
) -> None:
    async def post(
            request: web.Request,
            attr: Annotated[annotated_type, param_type],
    ) -> web.Response:
        assert attr == expected_data
        return web.Response()

    async def put(
            request: web.Request,
            attr: Annotated[annotated_type, param_type],
    ) -> web.Response:
        assert attr == expected_data
        return web.Response()

    app = Application()
    app.add_routes([web.post('/', post), web.put('/', put)])

    await _test(aiohttp_client, app, request_kw)


@pytest.mark.parametrize(
    "annotated_type, param_type, request_kw, expected_data",
    [
        param(str, Header, {'headers': {'attr': 'attr'}}, 'attr', id='header-param'),
        param(str, Cookie, {'cookies': {'attr': 'attr'}}, 'attr', id='cookie-param'),
        param(str, Query, {'params': {'attr': 'attr'}}, 'attr', id='query-param'),
        param(str, JsonBody, {'json': {'attr': 'attr'}}, 'attr', id='body-json-param'),
        param(str, FormDataBody, {'data': {'attr': 'attr'}}, 'attr', id='body-form-data-param'),
        param(Schema, HeaderSchema, {'headers': {'attr': 'attr'}}, Schema(attr='attr'), id='header-schema'),
        param(Schema, CookieSchema, {'cookies': {'attr': 'attr'}}, Schema(attr='attr'), id='cookie-schema'),
        param(Schema, QuerySchema, {'params': {'attr': 'attr'}}, Schema(attr='attr'), id='query-schema'),
        param(Schema, JsonBodySchema, {'json': {'attr': 'attr'}}, Schema(attr='attr'), id='body-json-schema'),
        param(Schema, FormDataBodySchema, {'data': {'attr': 'attr'}}, Schema(attr='attr'), id='body-form-schema'),
        param(Dict[str, Any], CookieRaw, {'cookies': {'attr': 'attr'}}, {'attr': 'attr'}, id='cookie-raw'),
        param(Dict[str, Any], QueryRaw, {'params': {'attr': 'attr'}}, {'attr': 'attr'}, id='query-raw'),
        param(Dict[str, Any], JsonBodyRaw, {'json': {'attr': 'attr'}}, {'attr': 'attr'}, id='body-json-raw'),
        param(Dict[str, Any], FormDataBodyRaw, {'data': {'attr': 'attr'}}, {'attr': 'attr'}, id='body-form-data-raw'),
    ],
)
async def test_success_func_def_with_routes_deco(
        aiohttp_client: AiohttpClient,
        annotated_type: Any,
        param_type: Any,
        request_kw: Dict[str, Any],
        expected_data: Any,
) -> None:

    routes = RouteTableDef()

    @routes.post('/')
    async def post(
            request: web.Request,
            attr: Annotated[annotated_type, param_type],
    ) -> web.Response:
        assert attr == expected_data
        return web.Response()

    @routes.put('/')
    async def put(
            request: web.Request,
            attr: Annotated[annotated_type, param_type],
    ) -> web.Response:
        assert attr == expected_data
        return web.Response()

    app = Application()
    app.add_routes(routes)

    await _test(aiohttp_client, app, request_kw)


@pytest.mark.parametrize(
    "annotated_type, param_type, request_kw, expected_data",
    [
        param(str, Header, {'headers': {'attr': 'attr'}}, 'attr', id='header-param'),
        param(str, Cookie, {'cookies': {'attr': 'attr'}}, 'attr', id='cookie-param'),
        param(str, Query, {'params': {'attr': 'attr'}}, 'attr', id='query-param'),
        param(str, JsonBody, {'json': {'attr': 'attr'}}, 'attr', id='body-json-param'),
        param(str, FormDataBody, {'data': {'attr': 'attr'}}, 'attr', id='body-form-data-param'),
        param(Schema, HeaderSchema, {'headers': {'attr': 'attr'}}, Schema(attr='attr'), id='header-schema'),
        param(Schema, CookieSchema, {'cookies': {'attr': 'attr'}}, Schema(attr='attr'), id='cookie-schema'),
        param(Schema, QuerySchema, {'params': {'attr': 'attr'}}, Schema(attr='attr'), id='query-schema'),
        param(Schema, JsonBodySchema, {'json': {'attr': 'attr'}}, Schema(attr='attr'), id='body-json-schema'),
        param(Schema, FormDataBodySchema, {'data': {'attr': 'attr'}}, Schema(attr='attr'), id='body-form-schema'),
        param(Dict[str, Any], CookieRaw, {'cookies': {'attr': 'attr'}}, {'attr': 'attr'}, id='cookie-raw'),
        param(Dict[str, Any], QueryRaw, {'params': {'attr': 'attr'}}, {'attr': 'attr'}, id='query-raw'),
        param(Dict[str, Any], JsonBodyRaw, {'json': {'attr': 'attr'}}, {'attr': 'attr'}, id='body-json-raw'),
        param(Dict[str, Any], FormDataBodyRaw, {'data': {'attr': 'attr'}}, {'attr': 'attr'}, id='body-form-data-raw'),
    ],
)
async def test_success_class_def_as_view(
        aiohttp_client: AiohttpClient,
        annotated_type: Any,
        param_type: Any,
        request_kw: Dict[str, Any],
        expected_data: Any,
) -> None:
    handler = _create_class_handler(annotated_type, param_type, expected_data)

    app = Application()
    app.add_routes([web.view('/', handler)])

    await _test(aiohttp_client, app, request_kw)


@pytest.mark.parametrize(
    "annotated_type, param_type, request_kw, expected_data",
    [
        param(str, Header, {'headers': {'attr': 'attr'}}, 'attr', id='header-param'),
        param(str, Cookie, {'cookies': {'attr': 'attr'}}, 'attr', id='cookie-param'),
        param(str, Query, {'params': {'attr': 'attr'}}, 'attr', id='query-param'),
        param(str, JsonBody, {'json': {'attr': 'attr'}}, 'attr', id='body-json-param'),
        param(str, FormDataBody, {'data': {'attr': 'attr'}}, 'attr', id='body-form-data-param'),
        param(Schema, HeaderSchema, {'headers': {'attr': 'attr'}}, Schema(attr='attr'), id='header-schema'),
        param(Schema, CookieSchema, {'cookies': {'attr': 'attr'}}, Schema(attr='attr'), id='cookie-schema'),
        param(Schema, QuerySchema, {'params': {'attr': 'attr'}}, Schema(attr='attr'), id='query-schema'),
        param(Schema, JsonBodySchema, {'json': {'attr': 'attr'}}, Schema(attr='attr'), id='body-json-schema'),
        param(Schema, FormDataBodySchema, {'data': {'attr': 'attr'}}, Schema(attr='attr'), id='body-form-schema'),
        param(Dict[str, Any], CookieRaw, {'cookies': {'attr': 'attr'}}, {'attr': 'attr'}, id='cookie-raw'),
        param(Dict[str, Any], QueryRaw, {'params': {'attr': 'attr'}}, {'attr': 'attr'}, id='query-raw'),
        param(Dict[str, Any], JsonBodyRaw, {'json': {'attr': 'attr'}}, {'attr': 'attr'}, id='body-json-raw'),
        param(Dict[str, Any], FormDataBodyRaw, {'data': {'attr': 'attr'}}, {'attr': 'attr'}, id='body-form-data-raw'),
    ],
)
async def test_success_class_def_as_subapp(
        aiohttp_client: AiohttpClient,
        annotated_type: Any,
        param_type: Any,
        request_kw: Dict[str, Any],
        expected_data: Any,
) -> None:
    handler = _create_class_handler(annotated_type, param_type, expected_data)

    app = Application()
    app.add_routes([web.post('/', handler), web.put('/', handler)])

    sup_app = Application()
    sup_app.add_routes([web.post('/', handler), web.put('/', handler)])

    app.add_subapp('/v1', sup_app)

    await _test(aiohttp_client, app, request_kw)
    await _test(aiohttp_client, app, request_kw, path='/v1/')


async def test_not_found(aiohttp_client: AiohttpClient) -> None:
    app = Application()
    client = await aiohttp_client(app)
    resp = await client.post('/')
    assert resp.status == HTTPStatus.NOT_FOUND


async def test_not_allowed(aiohttp_client: AiohttpClient) -> None:
    async def handler(request: web.Request) -> web.Response:
        pass

    app = Application()
    app.add_routes([web.get('/', handler)])
    client = await aiohttp_client(app)
    resp = await client.post('/')
    assert resp.status == HTTPStatus.METHOD_NOT_ALLOWED


def _create_class_handler(annotated_type: Any, param_type: Any, expected_data: Any) -> Any:
    class Foo(web.View):
        async def post(
                self,
                attr: Annotated[annotated_type, param_type],
        ) -> web.Response:
            assert attr == expected_data
            return web.Response()

        async def put(
                self,
                attr: Annotated[annotated_type, param_type],
        ) -> web.Response:
            assert attr == expected_data
            return web.Response()

    return Foo


async def _test(
        aiohttp_client: AiohttpClient,
        app: web.Application,
        request_kw: Dict[str, Any],
        path: str = '/',
) -> None:
    client = await aiohttp_client(app)
    resp = await client.post(path, **request_kw)
    assert resp.status == HTTPStatus.OK
    resp = await client.put(path, **request_kw)
    assert resp.status == HTTPStatus.OK
