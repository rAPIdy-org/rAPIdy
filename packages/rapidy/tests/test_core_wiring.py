from __future__ import annotations

from typing import Annotated, Any

import pytest
from rapidy_core.client_errors import normalize_errors
from rapidy_core.constants import (
    DEFAULT_JSON_DECODER as CORE_JSON_DECODER,
    DEFAULT_JSON_ENCODER as CORE_JSON_ENCODER,
)
from rapidy_core.enums import (
    Charset as CoreCharset,
    ContentType as CoreContentType,
    HeaderName as CoreHeaderName,
    HTTPRequestParamType,
)
from rapidy_core.exceptions import RapidyException as CoreRapidyException
from rapidy_core.parameters.http import (
    Body as CoreBody,
    Header as CoreHeader,
    PathParam as CorePathParam,
    QueryParam as CoreQueryParam,
)
from rapidy_core.signature import ParameterNotInstanceError

from rapidy._base_exceptions import RapidyException
from rapidy.constants import DEFAULT_JSON_DECODER, DEFAULT_JSON_ENCODER
from rapidy.endpoint_handlers.http.attrs_extractor import (
    get_http_handler_info,
    RequestFieldAlreadyExistsError,
)
from rapidy.endpoint_handlers.http.controller import ResponseValidationError
from rapidy.endpoint_handlers.http.request.data_extractors import ExtractJsonError
from rapidy.endpoint_handlers.http.request.data_validators import (
    RequestSingleParameterValidator,
    result_validator_factory,
)
from rapidy.exceptions import HTTPMethodNotAllowed
from rapidy.http import (
    Body,
    Charset,
    ContentType,
    Header,
    HeaderName,
    PathParam,
    QueryParam,
)
from rapidy.request import Request
from rapidy.response import Response
from rapidy.typedefs import Unset, View


def test_server_facade_preserves_core_identity() -> None:
    assert Body is CoreBody
    assert Header is CoreHeader
    assert PathParam is CorePathParam
    assert QueryParam is CoreQueryParam
    assert Charset is CoreCharset
    assert ContentType is CoreContentType
    assert HeaderName is CoreHeaderName
    assert DEFAULT_JSON_ENCODER is CORE_JSON_ENCODER
    assert DEFAULT_JSON_DECODER is CORE_JSON_DECODER
    assert RapidyException is CoreRapidyException


def test_http_attrs_extend_core_signature_information() -> None:
    async def handler(
        request: Request,
        response: Response,
        user_id: Annotated[int, PathParam()],
        token: str = Header(alias='x-token'),
    ) -> None:
        pass

    info = get_http_handler_info(handler, request_attr_can_declare_fst=True)

    assert info.request_attribute is not None
    assert info.request_attribute.attribute_name == 'request'
    assert info.response_attribute is not None
    assert info.response_attribute.attribute_name == 'response'
    assert [param.attribute_name for param in info.request_params] == ['user_id', 'token']
    assert [param.http_param_type for param in info.request_params] == [
        HTTPRequestParamType.path,
        HTTPRequestParamType.header,
    ]
    assert info.request_params[1].field_info.alias == 'x-token'


def test_signature_conflicts_are_owned_by_core() -> None:
    async def invalid(value: int = QueryParam) -> None:
        pass

    with pytest.raises(ParameterNotInstanceError):
        get_http_handler_info(invalid, request_attr_can_declare_fst=False)


def test_response_validation_error_keeps_pydantic_details() -> None:
    async def handler() -> None:
        pass

    error = ResponseValidationError.create_with_handler_validation_errors(
        handler,
        errors=[
            {
                'loc': ('response',),
                'msg': 'bad value',
                'type': 'value_error',
                'input': 'bad',
                'url': 'https://errors.pydantic.dev/example',
            }
        ],
    )
    assert "'input': 'bad'" in str(error)
    assert "'url': 'https://errors.pydantic.dev/example'" in str(error)


def test_duplicate_request_injection_is_rejected() -> None:
    async def invalid(first, second: Request) -> None:
        pass

    with pytest.raises(RequestFieldAlreadyExistsError):
        get_http_handler_info(invalid, request_attr_can_declare_fst=True)


@pytest.mark.asyncio
async def test_request_and_result_validation_use_core_fields() -> None:
    async def handler(age: int = QueryParam(gt=0)) -> int:
        return age

    info = get_http_handler_info(handler, request_attr_can_declare_fst=False)
    field_info = info.request_params[0].field_info

    async def valid_extractor(_: Request) -> dict[str, str]:
        return {'age': '4'}

    request_validator = RequestSingleParameterValidator(valid_extractor, HTTPRequestParamType.query)
    request_validator.add_field(field_info, handler)
    values, errors = await request_validator.validate(object())
    assert values == {'age': 4}
    assert errors == []

    async def invalid_extractor(_: Request) -> dict[str, str]:
        return {'age': 'wrong'}

    request_validator = RequestSingleParameterValidator(invalid_extractor, HTTPRequestParamType.query)
    request_validator.add_field(field_info, handler)
    values, errors = await request_validator.validate(object())
    assert values == {}
    assert errors
    assert errors[0]['loc'] == (HTTPRequestParamType.query, 'age')
    assert {'input', 'url'} <= errors[0].keys()
    assert normalize_errors(errors, pop_useless_keys=False)[0]['input'] == 'wrong'

    result_validator = result_validator_factory(handler, int, Unset)
    result, result_errors = await result_validator.validate('5')
    assert result == 5
    assert result_errors is None


@pytest.mark.asyncio
async def test_extraction_errors_keep_core_client_error_shape() -> None:
    async def handler(value: int = QueryParam()) -> None:
        pass

    field_info = get_http_handler_info(handler, request_attr_can_declare_fst=False).request_params[0].field_info

    async def failing_extractor(_: Request) -> Any:
        raise ExtractJsonError(json_decode_err_msg='bad json')

    validator = RequestSingleParameterValidator(failing_extractor, HTTPRequestParamType.query)
    validator.add_field(field_info, handler)
    values, errors = await validator.validate(object())
    assert values == {}
    assert errors
    assert errors[0]['loc'] == (HTTPRequestParamType.query,)
    assert errors[0]['type'] == 'ExtractError'


@pytest.mark.asyncio
async def test_view_dispatches_and_reports_allowed_methods() -> None:
    class ExampleView(View):
        async def get(self) -> str:
            return 'ok'

    request = object.__new__(Request)
    request.method = 'GET'
    assert await ExampleView(request) == 'ok'

    request.method = 'POST'
    with pytest.raises(HTTPMethodNotAllowed) as exc_info:
        await ExampleView(request)
    assert exc_info.value.allowed_methods == {'GET'}
