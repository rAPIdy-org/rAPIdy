import inspect
from typing import Any, Literal, Union

import pytest
from aiohttp.pytest_plugin import AiohttpClient
from pydantic import BaseModel

from rapidy import web
from rapidy.enums import ContentType, HeaderName
from rapidy.typedefs import CallNext
from tests.test_handlers.test_responses.test_extended_responses.helpers import (
    check_all_handlers,
    check_all_handlers_with_all_response_model_flows,
    DEFAULT_RETURN_VALUE,
    PATH,
    test_dict,
    TestBaseModel,
    TestDataclass,
)


async def test_validation_success(aiohttp_client: AiohttpClient) -> None:
    await check_all_handlers_with_all_response_model_flows(
        aiohttp_client=aiohttp_client,
        aiohttp_client_response_body_attr_name='text',
        # handler fabric attrs
        handler_return_type=str,
        handler_return_value=DEFAULT_RETURN_VALUE,
    )


@pytest.mark.parametrize('response_validate', [True, False])
async def test_validation_flag(aiohttp_client: AiohttpClient, response_validate: bool) -> None:
    await check_all_handlers_with_all_response_model_flows(
        aiohttp_client=aiohttp_client,
        aiohttp_client_response_body_attr_name='text',
        # handler fabric attrs
        handler_return_type=int,
        handler_return_value=DEFAULT_RETURN_VALUE,
        expected_validation_error=response_validate,
        # handler attrs
        response_validate=response_validate,
    )


@pytest.mark.parametrize(
    'return_type', [
        int,
        str,
        Union[int, str],
    ],
)  # no point to check everything
@pytest.mark.parametrize('response_validate', [True, False])
async def test_handler_return_none(aiohttp_client: AiohttpClient, response_validate: bool, return_type: Any) -> None:
    await check_all_handlers_with_all_response_model_flows(
        aiohttp_client=aiohttp_client,
        # handler fabric attrs
        handler_return_type=return_type,
        expected_validation_error=response_validate,
        handler_return_value=None,
        # handler attrs
        response_validate=response_validate,
    )


@pytest.mark.parametrize(
    'return_type', [
        web.Response,
        Any,
        None,
        inspect.Signature.empty,
    ],
)
@pytest.mark.parametrize('response_validate', [True, False])
async def test_return_none_unsupported_validation_types(
        aiohttp_client: AiohttpClient, return_type: Any, response_validate: bool,
) -> None:
    await check_all_handlers(
        aiohttp_client=aiohttp_client,
        # handler fabric attrs
        handler_return_type=return_type,
        handler_return_value=None,
        # handler attrs
        response_validate=response_validate,
    )


@pytest.mark.parametrize('schema', [TestDataclass, TestBaseModel])
async def test_cast_dict_to_schema(aiohttp_client: AiohttpClient, schema: Any) -> None:
    await check_all_handlers_with_all_response_model_flows(
        aiohttp_client=aiohttp_client,
        # handler fabric attrs
        handler_return_type=schema,
        handler_return_value=test_dict,
        expected_return_value=test_dict,
    )


class TestCaseResponseBodyType(BaseModel):
    id: str

    handler_return_value: str = DEFAULT_RETURN_VALUE
    expected_return_value: Any = DEFAULT_RETURN_VALUE

    content_type: ContentType
    client_attr_name: Literal['text', 'json', 'read']

    __test__ = False


test_body_types_cases = (
    # TODO: more body types
    TestCaseResponseBodyType(
        id='json',
        content_type=ContentType.json,
        client_attr_name='json',
    ),
    TestCaseResponseBodyType(
        id='text',
        content_type=ContentType.text_plain,
        client_attr_name='text',
    ),
    TestCaseResponseBodyType(
        id='binary',
        content_type=ContentType.stream,
        client_attr_name='read',
        expected_return_value=DEFAULT_RETURN_VALUE.encode(),
    ),
)


@pytest.mark.parametrize('test_case', [pytest.param(test_case, id=test_case.id) for test_case in test_body_types_cases])
async def test_body_types(aiohttp_client: AiohttpClient, test_case: TestCaseResponseBodyType) -> None:
    await check_all_handlers_with_all_response_model_flows(
        aiohttp_client=aiohttp_client,
        # handler fabric attrs
        handler_return_type=str,
        handler_return_value=test_case.handler_return_value,
        expected_return_value=test_case.expected_return_value,
        aiohttp_client_response_body_attr_name=test_case.client_attr_name,
        # handler attrs
        response_content_type=test_case.content_type,
    )


async def test_direct_response_ignore_pre_added_data(aiohttp_client: AiohttpClient) -> None:
    another_text_return_value: str = 'another_test_value'
    another_response_content_type: str = 'text/html'

    async def handler(response: web.Response) -> web.Response:
        response.text = DEFAULT_RETURN_VALUE
        return web.Response(
            body=another_text_return_value,
            headers={HeaderName.content_type: another_response_content_type},
        )

    app = web.Application()
    app.router.add_get(PATH, handler, response_content_type=ContentType.json)

    client = await aiohttp_client(app)
    resp = await client.get(PATH)

    assert await resp.text() == another_text_return_value
    assert resp.headers[HeaderName.content_type].startswith(another_response_content_type)


async def test_injected_response(aiohttp_client: AiohttpClient) -> None:
    async def handler(response: web.Response) -> web.Response:
        response.text = DEFAULT_RETURN_VALUE
        return response

    app = web.Application()
    app.router.add_get(PATH, handler, response_content_type=ContentType.json)

    client = await aiohttp_client(app)
    resp = await client.get(PATH)

    assert await resp.text() == DEFAULT_RETURN_VALUE


async def test_update_data_for_injected_response(aiohttp_client: AiohttpClient) -> None:
    async def handler(response: web.Response) -> None:
        response.body = DEFAULT_RETURN_VALUE

    app = web.Application()
    app.router.add_get(PATH, handler, response_content_type=ContentType.json)

    client = await aiohttp_client(app)
    resp = await client.get(PATH)

    assert await resp.json() == DEFAULT_RETURN_VALUE


@pytest.mark.parametrize('create_web_response', [True, False])
@pytest.mark.parametrize('return_middleware', [True, False])
async def test_union_stream_response(
        aiohttp_client: AiohttpClient,
        create_web_response: bool,
        return_middleware: bool,
) -> None:
    async def handler() -> Union[web.Response, str]:
        if create_web_response:
            return web.Response(DEFAULT_RETURN_VALUE)
        return DEFAULT_RETURN_VALUE

    @web.middleware
    async def middleware(request: web.Request, handler: CallNext) -> Union[web.StreamResponse, str]:
        if return_middleware:
            if create_web_response:
                return web.Response(DEFAULT_RETURN_VALUE)
            return DEFAULT_RETURN_VALUE
        return await handler(request)

    app = web.Application(middlewares=[middleware])
    app.router.add_get(PATH, handler)

    client = await aiohttp_client(app)
    resp = await client.get(PATH)

    assert await resp.text() == DEFAULT_RETURN_VALUE
