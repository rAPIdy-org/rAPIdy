from http import HTTPStatus
from typing import Any
from unittest import mock

from aiohttp import MultipartWriter, Payload
from aiohttp.helpers import content_disposition_header
from pydantic import BaseModel
from pytest_aiohttp.plugin import AiohttpClient
from typing_extensions import Annotated

from rapidy import hdrs, web
from rapidy._version import AIOHTTP_VERSION_TUPLE
from rapidy.request_params import JsonBodySchema, MultipartBodySchema
from tests.helpers import create_content_type_header, create_multipart_headers


class Schema(BaseModel):
    pass


async def test_failure_json_with_default_decoder(aiohttp_client: AiohttpClient) -> None:
    async def handler(
            body_data: Annotated[Schema, JsonBodySchema()],
    ) -> web.Response:
        pass

    app = web.Application()
    app.add_routes([web.post('/', handler)])

    client = await aiohttp_client(app)
    resp = await client.post('/', data='}[{{}')

    assert resp.status == HTTPStatus.UNPROCESSABLE_ENTITY
    resp_json = await resp.json()

    assert resp_json == {
        'errors': [
            {
                'loc': ['body'],
                'msg': 'Failed to extract body data as Json: Expecting value: line 1 column 1 (char 0)',
                'type': 'body_extraction',
            },
        ],
    }


async def test_multipart_content_type_expected(
        aiohttp_client: AiohttpClient,
        multipart_writer: MultipartWriter,
) -> None:
    async def handler(
            body_data: Annotated[Schema, MultipartBodySchema()],
    ) -> web.Response:
        pass

    app = web.Application()
    app.add_routes([web.post('/', handler)])

    client = await aiohttp_client(app)

    resp = await client.post('/', data='-')

    assert resp.status == HTTPStatus.UNPROCESSABLE_ENTITY

    assert await resp.json() == {
        'errors': [
            {
                'loc': ['body'],
                'msg': 'Failed to extract body data as Multipart: multipart/* content type expected',
                'type': 'body_extraction',
            },
        ],
    }


async def test_multipart_boundary_expected(aiohttp_client: AiohttpClient) -> None:
    async def handler(
            body_data: Annotated[Schema, MultipartBodySchema()],
    ) -> web.Response:
        pass

    app = web.Application()
    app.add_routes([web.post('/', handler)])

    client = await aiohttp_client(app)

    resp = await client.post(
        '/',
        headers={'Content-Type': 'multipart/form-data'},
        data='-',
    )

    assert resp.status == HTTPStatus.UNPROCESSABLE_ENTITY

    assert await resp.json() == {
        'errors': [
            {
                'loc': ['body'],
                'msg': 'Failed to extract body data as Multipart: boundary missed for Content-Type: '
                       'multipart/form-data',
                'type': 'body_extraction',
            },
        ],
    }


async def test_multipart_part_cannot_find_part_boundary(aiohttp_client: AiohttpClient) -> None:
    async def handler(
            body_data: Annotated[Schema, MultipartBodySchema()],
    ) -> web.Response:
        pass

    app = web.Application()
    app.add_routes([web.post('/', handler)])

    client = await aiohttp_client(app)

    resp = await client.post(
        '/',
        headers={'Content-Type': 'multipart/form-data; boundary=-'},
        data='-',
    )

    assert resp.status == HTTPStatus.UNPROCESSABLE_ENTITY

    assert await resp.json() == {
        'errors': [
            {
                'loc': ['body'],
                'msg': 'Failed to extract body data as Multipart. Failed to read part `1`: Could not find '
                       f'starting boundary b{"---"!r}',
                'type': 'body_extraction',
            },
        ],
    }


async def test_multipart_part_missing_content_type_error(
    aiohttp_client: AiohttpClient,
) -> None:
    async def handler(
            body_data: Annotated[Schema, MultipartBodySchema()],
    ) -> web.Response:
        pass

    app = web.Application()
    app.add_routes([web.post('/', handler)])

    client = await aiohttp_client(app)

    resp = await client.post(
        '/',
        headers={'Content-Type': 'multipart/form-data; boundary=12345'},
        data='--12345 \n'
        'Content-Disposition: form-data; name="text" \n\n'
        'asdasdsdd \n'
        '--12345--',
    )

    assert resp.status == HTTPStatus.UNPROCESSABLE_ENTITY

    assert await resp.json() == {
        'errors': [
            {
                'loc': ['body'],
                'msg': 'Failed to extract body data as Multipart. Failed to read part `1`: Part missing '
                       'Content-Type header',
                'type': 'body_extraction',
            },
        ],
    }


if AIOHTTP_VERSION_TUPLE != (3, 9, 4):
    # In Aiohttp 3.9.4, the MultipartWriter structure has been changed, so ... test compatibility is broken.
    def patch_set_content_disposition(
            self: Payload, disptype: str, quote_fields: bool = True, _charset: str = "utf-8", **params: Any,
    ) -> None:
        params.pop('name', None)
        self._headers[hdrs.CONTENT_DISPOSITION] = content_disposition_header(
            disptype, quote_fields=quote_fields, _charset=_charset, **params,
        )


    async def test_multipart_part_1_doesnt_has_name(
            aiohttp_client: AiohttpClient,
            multipart_writer: MultipartWriter,
    ) -> None:
        async def handler(
                body_data: Annotated[Schema, MultipartBodySchema()],
        ) -> web.Response:
            pass

        app = web.Application()
        app.add_routes([web.post('/', handler)])

        client = await aiohttp_client(app)

        with mock.patch('aiohttp.multipart.Payload.set_content_disposition', new=patch_set_content_disposition):
            multipart_writer.append('1', create_content_type_header())

        # is done to ignore MultipartWriter assertions.
        # because we check when the part.name is not present
        #
        # if self._is_form_data:
        #     ...
        #     assert "name=" in part.headers[CONTENT_DISPOSITION]
        #     ...
        #
        multipart_writer._is_form_data = False

        resp = await client.post('/', data=multipart_writer)

        assert resp.status == HTTPStatus.UNPROCESSABLE_ENTITY

        json_response = await resp.json()
        assert json_response == {
            'errors': [
                {
                    'loc': ['body'],
                    'msg': 'Failed to extract body data as Multipart. Failed to read part `1`: Content-Disposition '
                           'header doesnt contain `name` attr',
                    'type': 'body_extraction',
                },
            ],
        }


    async def test_multipart_part_2_doesnt_has_name(
        aiohttp_client: AiohttpClient,
        multipart_writer: MultipartWriter,
    ) -> None:
        async def handler(
                body_data: Annotated[Schema, MultipartBodySchema()],
        ) -> web.Response:
            pass

        app = web.Application()
        app.add_routes([web.post('/', handler)])

        client = await aiohttp_client(app)

        multipart_writer.append('1', create_multipart_headers(part_name='key'))

        with mock.patch('aiohttp.multipart.Payload.set_content_disposition', new=patch_set_content_disposition):
            multipart_writer.append('2', create_content_type_header())

        # is done to ignore MultipartWriter assertions.
        # because we check when the part.name is not present
        #
        # if self._is_form_data:
        #     ...
        #     assert "name=" in part.headers[CONTENT_DISPOSITION]
        #     ...
        #
        multipart_writer._is_form_data = False

        resp = await client.post('/', data=multipart_writer)

        assert resp.status == HTTPStatus.UNPROCESSABLE_ENTITY

        json_response = await resp.json()
        assert json_response == {
            'errors': [
                {
                    'loc': ['body'],
                    'msg': 'Failed to extract body data as Multipart. Failed to read part `2`: Content-Disposition '
                           'header doesnt contain `name` attr',
                    'type': 'body_extraction',
                },
            ],
        }
