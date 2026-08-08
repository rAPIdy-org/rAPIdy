import inspect
from typing import Any

import pytest
from aiohttp.pytest_plugin import AiohttpClient

from rapidy.http import Response
from tests.app_checkers import check_handlers, check_handlers_all_response_models


@pytest.mark.parametrize('response_validate', [True, False])
async def test_validation_flag(aiohttp_client: AiohttpClient, response_validate: bool) -> None:
    await check_handlers_all_response_models(
        aiohttp_client=aiohttp_client,
        # handler fabric attrs
        handler_return_type=int,
        check_return_value=not response_validate,
        expected_status_code=500 if response_validate else 200,
        # handler attrs
        response_validate=response_validate,
    )


@pytest.mark.parametrize(
    'return_type',
    [
        int,
        str,
        int | str,
    ],
)  # no point to check everything
@pytest.mark.parametrize('response_validate', [True, False])
async def test_handler_return_none(aiohttp_client: AiohttpClient, response_validate: bool, return_type: Any) -> None:
    await check_handlers_all_response_models(
        aiohttp_client=aiohttp_client,
        # handler fabric attrs
        handler_return_type=return_type,
        check_return_value=not response_validate,
        expected_status_code=500 if response_validate else 200,
        handler_return_value=None,
        expected_return_value=None,
        # handler attrs
        response_validate=response_validate,
    )


@pytest.mark.parametrize(
    'return_type',
    [
        Response,
        Any,
        None,
        inspect.Signature.empty,
    ],
)
@pytest.mark.parametrize('response_validate', [True, False])
async def test_return_none_unsupported_validation_types(
    aiohttp_client: AiohttpClient,
    return_type: Any,
    response_validate: bool,
) -> None:
    await check_handlers(
        aiohttp_client=aiohttp_client,
        # handler fabric attrs
        handler_return_type=return_type,
        handler_return_value=None,
        # handler attrs
        response_validate=response_validate,
    )
