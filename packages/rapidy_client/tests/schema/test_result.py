from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import FrozenInstanceError
from typing import Annotated

import pytest
from pydantic import BaseModel
from rapidy_client import (
    URL,
    BodyTooLargeError,
    DecodeError,
    Headers,
    HttpClient,
    Request,
    RequestExtensions,
    Response,
    ResponseExtensions,
    ResponseValidationError,
    Result,
    SchemaDefinitionError,
    StatusError,
    Timeout,
    UpstreamConfig,
    bind,
)
from rapidy_client.config import RedirectConfig
from rapidy_client.schema import PathParam, Stream, get
from rapidy_client.schema._serialize import (
    ResponseKind,
    build_response_plan,
    parse_response,
)
from rapidy_client.testing import MockTransport
from rapidy_core import UNSET


class Model(BaseModel):
    identifier: int


class ErrorModel(BaseModel):
    code: str


async def _stream(body: bytes) -> AsyncIterator[bytes]:
    if body:
        yield body


def _response(
    *,
    status: int,
    body: bytes = b"",
    headers: Headers | None = None,
    on_close: Callable[[], Awaitable[None]] | None = None,
    max_response_size: int | None = None,
) -> Response:
    request = Request(
        method="GET",
        url=URL("https://response.example.test/value"),
        headers=Headers(),
        content=None,
        extensions=RequestExtensions(
            upstream="response-test",
            endpoint="/value",
            request_id="request-1",
            timeout=Timeout(),
            retry=None,
            idempotent=True,
            auth_override=UNSET,
            deadline=None,
            redirects=RedirectConfig(),
        ),
    )
    return Response(
        status=status,
        headers=headers or Headers(),
        request=request,
        extensions=ResponseExtensions(elapsed=0.0, attempt=1),
        stream=_stream(body),
        on_close=on_close,
        max_response_size=max_response_size,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("annotation", "status", "body", "expected"),
    [
        (Model, 200, b'{"identifier": 7}', Model(identifier=7)),
        (Model | None, 404, b"ignored", None),
        (None, 204, b"ignored", None),
    ],
)
async def test_response_matrix_values(
    annotation: object,
    status: int,
    body: bytes,
    expected: object,
) -> None:
    statuses = {404: None} if status == 404 else None
    plan = build_response_plan(return_annotation=annotation, statuses=statuses)

    assert await parse_response(_response(status=status, body=body), plan) == expected


@pytest.mark.asyncio
async def test_statuses_model_value() -> None:
    plan = build_response_plan(
        return_annotation=Model | ErrorModel,
        statuses={409: ErrorModel},
    )

    result = await parse_response(
        _response(status=409, body=b'{"code":"conflict"}'), plan
    )

    assert result == ErrorModel(code="conflict")


@pytest.mark.asyncio
async def test_raw_response_buffered_pool_return_on_any_status() -> None:
    closed = 0

    async def close() -> None:
        nonlocal closed
        closed += 1

    response = _response(status=503, body=b"raw-error", on_close=close)
    plan = build_response_plan(return_annotation=Response)

    result = await parse_response(response, plan)

    assert result is response
    assert await result.aread() == b"raw-error"
    assert closed == 1


@pytest.mark.asyncio
async def test_return_none_reads_body_and_returns_pool() -> None:
    closed = False

    async def close() -> None:
        nonlocal closed
        closed = True

    plan = build_response_plan(return_annotation=None)

    assert (
        await parse_response(
            _response(status=200, body=b"ignored", on_close=close), plan
        )
        is None
    )
    assert closed


@pytest.mark.asyncio
async def test_response_validation_and_decode_errors_close_body() -> None:
    validated = build_response_plan(return_annotation=Model)
    with pytest.raises(ResponseValidationError):
        await parse_response(
            _response(status=200, body=b'{"identifier":"bad"}'), validated
        )

    unvalidated = build_response_plan(return_annotation=Model, response_validate=False)
    with pytest.raises(DecodeError):
        await parse_response(_response(status=200, body=b"not-json"), unvalidated)


@pytest.mark.asyncio
async def test_response_validate_false_constructs_without_validation() -> None:
    plan = build_response_plan(return_annotation=Model, response_validate=False)

    result = await parse_response(
        _response(status=200, body=b'{"identifier":"trusted"}'), plan
    )

    assert isinstance(result, Model)
    assert result.identifier == "trusted"


@pytest.mark.asyncio
async def test_response_type_overrides_annotation() -> None:
    plan = build_response_plan(return_annotation=Model, response_type=ErrorModel)

    result = await parse_response(
        _response(status=200, body=b'{"code":"override"}'), plan
    )

    assert result == ErrorModel(code="override")


@pytest.mark.asyncio
async def test_error_model_single_and_mapping() -> None:
    single_plan = build_response_plan(return_annotation=Model, error_model=ErrorModel)
    with pytest.raises(StatusError) as single_error:
        await parse_response(
            _response(status=500, body=b'{"code":"boom"}'), single_plan
        )
    assert single_error.value.error_model == ErrorModel(code="boom")
    assert single_error.value.upstream == "response-test"
    assert single_error.value.endpoint == "/value"
    assert single_error.value.request_id == "request-1"

    mapping_plan = build_response_plan(
        return_annotation=Model, error_model={500: ErrorModel}
    )
    with pytest.raises(StatusError) as mapped_error:
        await parse_response(
            _response(status=503, body=b'{"code":"ignored"}'), mapping_plan
        )
    assert mapped_error.value.error_model is None


@pytest.mark.asyncio
async def test_error_model_invalid_or_capped_body_is_not_attached() -> None:
    plan = build_response_plan(return_annotation=Model, error_model=ErrorModel)

    with pytest.raises(StatusError) as invalid:
        await parse_response(_response(status=500, body=b"invalid"), plan)
    assert invalid.value.error_model is None

    with pytest.raises(StatusError) as capped:
        await parse_response(
            _response(status=500, body=b"x" * 100),
            plan,
            error_body_limit=8,
        )
    assert capped.value.error_model is None
    assert await capped.value.response.aread() == b"x" * 8


@pytest.mark.asyncio
async def test_result_success_and_declared_status_metadata() -> None:
    headers = Headers({"x-trace": "trace-1"})
    success_plan = build_response_plan(return_annotation=Result[Model])

    success = await parse_response(
        _response(
            status=200,
            body=b'{"identifier":7}',
            headers=headers,
        ),
        success_plan,
    )

    assert success == Result(value=Model(identifier=7), status=200, headers=headers)
    with pytest.raises(FrozenInstanceError):
        success.status = 201

    missing_plan = build_response_plan(
        return_annotation=Result[Model | None], statuses={404: None}
    )
    missing = await parse_response(_response(status=404), missing_plan)
    assert missing.value is None
    assert missing.status == 404


@pytest.mark.asyncio
async def test_result_declared_model_and_undeclared_error() -> None:
    plan = build_response_plan(
        return_annotation=Result[Model | ErrorModel],
        statuses={409: ErrorModel},
    )
    declared = await parse_response(
        _response(status=409, body=b'{"code":"conflict"}'), plan
    )
    assert declared.value == ErrorModel(code="conflict")
    assert declared.status == 409

    with pytest.raises(StatusError):
        await parse_response(_response(status=503, body=b"down"), plan)


@pytest.mark.parametrize(
    "annotation",
    [Result[Response], Result[Stream]],
)
def test_result_raw_and_stream_are_rejected(annotation: object) -> None:
    with pytest.raises(SchemaDefinitionError, match="forbidden"):
        build_response_plan(return_annotation=annotation)


def test_result_raw_is_rejected_by_bind_before_io() -> None:
    @get("/raw")
    async def raw() -> Result[Response]:
        raise NotImplementedError

    mock = MockTransport()
    with pytest.raises(SchemaDefinitionError, match="raw"):
        bind(raw, _client(mock))
    assert not mock.calls


def test_invalid_status_collision_and_unsupported_return_are_rejected() -> None:
    with pytest.raises(SchemaDefinitionError, match="invalid status"):
        build_response_plan(return_annotation=Model | None, statuses={999: None})
    with pytest.raises(SchemaDefinitionError, match="statuses and error_model"):
        build_response_plan(
            return_annotation=Model | ErrorModel,
            statuses={409: ErrorModel},
            error_model={409: ErrorModel},
        )
    with pytest.raises(SchemaDefinitionError, match="unsupported return"):
        build_response_plan(return_annotation=int)


@pytest.mark.asyncio
async def test_stream_plan_is_classified_but_not_buffered() -> None:
    plan = build_response_plan(return_annotation=Stream)
    assert plan.kind is ResponseKind.STREAM
    with pytest.raises(NotImplementedError, match="milestone 18"):
        await parse_response(_response(status=200, body=b"stream"), plan)


@pytest.mark.asyncio
async def test_body_too_large_propagates() -> None:
    plan = build_response_plan(return_annotation=Model)
    with pytest.raises(BodyTooLargeError):
        await parse_response(
            _response(
                status=200,
                body=b'{"identifier":123}',
                max_response_size=4,
            ),
            plan,
        )


def _client(mock: MockTransport) -> HttpClient:
    return HttpClient(
        UpstreamConfig(base_url="https://result.example.test"), transport=mock
    )


@pytest.mark.asyncio
async def test_bound_result_endpoint_uses_dispatcher() -> None:
    @get("/invoices/{invoice_id}", statuses={404: None})
    async def invoice(invoice_id: Annotated[str, PathParam()]) -> Result[Model | None]:
        raise NotImplementedError

    found_mock = MockTransport()
    found_mock.route("GET", "/invoices/7").respond(json={"identifier": 7})
    missing_mock = MockTransport()
    missing_mock.route("GET", "/invoices/8").respond(status=404)

    found = await bind(invoice, _client(found_mock))("7")
    missing = await bind(invoice, _client(missing_mock))("8")

    assert found == Result(
        value=Model(identifier=7),
        status=200,
        headers=found.headers,
    )
    assert missing.value is None
    assert missing.status == 404
