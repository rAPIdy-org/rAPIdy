from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated

import pytest
from rapidy_client import (
    ConnectError,
    HttpClient,
    Request,
    Response,
    UpstreamConfig,
    bind,
    get,
)
from rapidy_client.schema import Header, PathParam, QueryParam
from rapidy_client.testing import MockRouteError, MockTransport


def _client(mock: MockTransport) -> HttpClient:
    return HttpClient(
        UpstreamConfig.model_validate(
            {
                "base_url": "https://mock.test",
                "retry": {"max_attempts": 3, "budget_ratio": None},
                "log": {"level": "off"},
            }
        ),
        transport=mock,
    )


class _AttemptRecorder:
    def __init__(self) -> None:
        self.attempts: list[int] = []

    async def __call__(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        self.attempts.append(request.extensions.attempt)
        return await call_next(request)


@pytest.mark.asyncio
async def test_mock_sequence_runs_through_complete_client_stack() -> None:
    mock = MockTransport()
    failure = ConnectError("temporarily unavailable")
    mock.route("GET", "/flaky").times(2).raise_(failure).then().respond(
        status=200, json={"ok": True}
    )
    recorder = _AttemptRecorder()
    client = HttpClient(
        UpstreamConfig.model_validate(
            {
                "base_url": "https://mock.test",
                "retry": {"max_attempts": 3, "budget_ratio": None},
                "log": {"level": "off"},
            }
        ),
        transport=mock,
        per_attempt_middlewares=(recorder,),
    )
    try:
        response = await client.get("/flaky")
    finally:
        await client.aclose()

    assert response.status == 200
    assert await response.json() == {"ok": True}
    assert recorder.attempts == [1, 2, 3]
    assert response.extensions.attempt == 3
    assert isinstance(mock.calls[0].exception, ConnectError)
    assert isinstance(mock.calls[1].exception, ConnectError)
    assert mock.calls[2].response is response
    mock.assert_called("GET", "/flaky", times=3)


@pytest.mark.asyncio
async def test_unmatched_route_diagnostic_survives_client_stack() -> None:
    mock = MockTransport()
    mock.route("GET", "/known/{id}").respond()
    client = _client(mock)
    try:
        with pytest.raises(MockRouteError) as captured:
            await client.get("/unknown")
    finally:
        await client.aclose()

    assert captured.value.registered == ["GET /known/{id}"]
    assert "GET /unknown" in str(captured.value)
    assert "GET /known/{id}" in str(captured.value)


@pytest.mark.asyncio
async def test_default_and_annotated_markers_build_equivalent_requests() -> None:
    @get("/users/{user_id}")
    async def defaults(
        user_id: str = PathParam(),
        verbose: bool = QueryParam(alias="full"),
        trace: str = Header(alias="x-trace"),
    ) -> Response:
        raise NotImplementedError

    @get("/users/{user_id}")
    async def annotated(
        user_id: Annotated[str, PathParam()],
        verbose: Annotated[bool, QueryParam(alias="full")],
        trace: Annotated[str, Header(alias="x-trace")],
    ) -> Response:
        raise NotImplementedError

    first_mock = MockTransport()
    first_mock.route("GET", "/users/42").respond()
    second_mock = MockTransport()
    second_mock.route("GET", "/users/42").respond()
    first_client = _client(first_mock)
    second_client = _client(second_mock)
    try:
        await bind(defaults, first_client)("42", True, "trace-42")
        await bind(annotated, second_client)("42", True, "trace-42")
    finally:
        await first_client.aclose()
        await second_client.aclose()

    first = first_mock.calls[0].request
    second = second_mock.calls[0].request
    assert first.method == second.method == "GET"
    assert first.url._raw_str() == second.url._raw_str()
    assert first.headers.multi_items() == second.headers.multi_items()
    assert first.extensions.endpoint == second.extensions.endpoint
    assert first.extensions.idempotent == second.extensions.idempotent
